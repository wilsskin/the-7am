"""python -m brief.render [--lenient] [--preview]

Reads run/data.json, run/calendar.json and run/content.json, checks content.json against
the rules (BUILD_PLAN.md §6, §7), and writes run/issue.html, run/issue.txt and
run/render.json (subject, icons used, warnings) for brief.send.

Strict by default: if content.json breaks a rule Claude can fix (bad domain, meme not in
the candidates, unknown ticker, schema error), it prints the problems and exits 2 without
writing. Claude fixes content.json once and re-runs. If it still fails, run with
--lenient: invalid items are dropped and the rest renders. The email always sends.

Automatic either way: duplicate stories are dropped by priority, over-long lists are
trimmed, numbers in prose that aren't in data.json are flagged as warnings.
"""
import argparse

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import TypeAdapter, ValidationError

from brief import fmt, tokens
from brief.common import ET, ROOT, RUN_DIR, load_config, now_et
from brief.schema import Calendar, Content, Data, MoverStory

MAX_BYTES = 95_000          # Gmail clips at ~102KB; fail loudly before that
LEAD_INS = ("Why it matters:",)
# Six lines on an iPhone. The 358px mobile column fits ~43 characters per 16px line (measured
# Nov 25, 2026), so 6 lines is ~255 characters. This counts an inline headline and the link at
# the end of the paragraph. Longer paragraphs are split at a sentence break.
MAX_PARA_CHARS = 250
ARROW = "\u2197\ufe0e"   # ↗ forced to text, so iOS doesn't swap in the emoji
ABBREVS = {"mr", "mrs", "ms", "dr", "st", "inc", "corp", "co", "ltd", "jr", "sr", "vs", "no", "gov", "sen", "rep",
           "gen", "jan", "feb", "mar", "apr", "aug", "sept", "sep", "oct", "nov", "dec", "est", "approx"}
LATEST_LABELS = {"business": "Business", "tech": "Tech", "world": "World",
                 "pop_culture": "Pop culture", "sports": "Sports"}
# SF Symbol PNG shown inside each tag pill (templates/icons/tag-*.png).
LATEST_ICONS = {"Business": "tag-business", "Tech": "tag-tech", "World": "tag-world",
                "Pop culture": "tag-pop", "Sports": "tag-sports"}
# Word caps (warn only). Global target 1,600–1,900 (weekend ~1,000).
CAPS = {"big_read": 380, "top_3": 130, "holdings": 90, "off_the_clock": 90, "standout": 80, "desc": 30}
TRIM_ABOVE = {"weekday": 2200, "monday": 2300, "holiday": 2200, "weekend": 1300}
UNAVAILABLE_NAMES = {"markets": "Markets", "standout": "Big movers", "earnings": "Earnings",
                     "weather": "Weather", "mta": "Subway alerts", "sports": "Scores",
                     "memes": "Meme roundup", "market_calendar": "Market calendar"}


class RenderError(Exception):
    pass


# ---------- loading ----------

def load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return None


def parse_content(raw: dict | None, lenient: bool, errors: list[str]) -> Content | None:
    if raw is None:
        errors.append("content.json is missing")
        return None
    try:
        return Content.model_validate(raw)
    except ValidationError as e:
        for err in e.errors():
            errors.append(f"content.json {'.'.join(map(str, err['loc']))}: {err['msg']}")
        if not lenient:
            return None
    # Lenient: keep every field that validates on its own, drop the rest.
    good = {}
    for name, field in Content.model_fields.items():
        if name not in raw:
            continue
        try:
            good[name] = TypeAdapter(field.annotation).validate_python(raw[name])
        except ValidationError:
            if name in ("top_3", "holdings_news", "off_the_clock", "your_day_nyc", "memes", "on_deck_today", "movers"):
                good[name] = keep_valid_items(field.annotation, raw[name])
    if isinstance(good.get("top_3"), list):
        good["top_3"] = good["top_3"][:3]
    if isinstance(good.get("subject"), str):
        good["subject"] = good["subject"][:70]
    return Content.model_construct(**{"date": None, "edition": None, "subject": None, "intro": "",
                                      "section_desc": {}, "latest": {}, "your_day_nyc": [], "on_deck_today": [],
                                      "holdings_news": [], "top_3": [], "off_the_clock": [], "memes": [],
                                      "standout": None, "movers": [], "big_read": None, **good})


def keep_valid_items(annotation, items) -> list:
    item_type = annotation.__args__[0]
    out = []
    for it in items if isinstance(items, list) else []:
        try:
            out.append(TypeAdapter(item_type).validate_python(it))
        except ValidationError:
            pass
    return out


# ---------- rules ----------

def host_allowed(url: str, allowed: list[str]) -> bool:
    host = (urlparse(str(url)).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in allowed)


def norm_url(url) -> str:
    p = urlparse(str(url))
    return (p.hostname or "").removeprefix("www.") + p.path.rstrip("/")


STOPWORDS = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "at", "by", "from", "as",
             "its", "is", "after", "over", "into", "new"}


def similar(a: str, b: str) -> bool:
    """Near-duplicate headlines: at least 75% of their meaningful words are shared.
    Conservative on purpose; exact duplicates are caught by URL."""
    wa = {w for w in re.findall(r"[a-z0-9]+", a.lower()) if w not in STOPWORDS}
    wb = {w for w in re.findall(r"[a-z0-9]+", b.lower()) if w not in STOPWORDS}
    if not wa or not wb:
        return False
    return len(wa & wb) / len(wa | wb) >= 0.75


def words(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def items_by_priority(c: Content):
    """(section, list, index, url, title) in placement priority: Big Read > Top 3 > Holdings >
    Before the Bell > The Latest > Around NYC > Off the Clock (BUILD_PLAN.md §6)."""
    if c.big_read:
        yield "big_read", None, 0, c.big_read.link.url, c.big_read.headline
    for i, s in enumerate(c.top_3):
        yield "top_3", c.top_3, i, s.link.url, s.headline
    for i, s in enumerate(c.holdings_news):
        yield "holdings", c.holdings_news, i, s.link.url, s.headline
    for i, s in enumerate(c.movers):
        yield "movers", c.movers, i, s.link.url, s.link.title
    for k, links in c.latest.items():
        for i, l in enumerate(links):
            yield f"latest.{k}", links, i, l.url, l.title
    for i, l in enumerate(c.your_day_nyc):
        yield "your_day_nyc", c.your_day_nyc, i, l.url, l.title
    for i, s in enumerate(c.off_the_clock):
        yield "off_the_clock", c.off_the_clock, i, s.link.url, s.headline


def dedupe(c: Content, warnings: list[str]) -> None:
    seen = []
    drop = []
    for section, lst, i, url, title in items_by_priority(c):
        u = norm_url(url)
        dup = next((s for s in seen if s[0] == u or similar(s[1], title)), None)
        if dup:
            warnings.append(f'dropped duplicate in {section}: "{title}" (already in {dup[2]})')
            drop.append((section, lst, i))
        else:
            seen.append((u, title, section))
    for section, lst, i in reversed(drop):
        if lst is None:
            setattr(c, section, None)
        else:
            lst.pop(i)


def check_links(c: Content, cfg: dict, lenient: bool, errors: list[str]) -> None:
    allowed = cfg["sources"]["allowed"]
    leisure = allowed + cfg["sources"].get("off_the_clock_extra", [])
    bad = []
    for section, lst, i, url, title in items_by_priority(c):
        if not host_allowed(url, leisure if section == "off_the_clock" else allowed):
            errors.append(f'{section}: "{title}" links to {urlparse(str(url)).hostname}, not an allowed source')
            bad.append((section, lst, i))
    if lenient:
        for section, lst, i in reversed(bad):
            if lst is None:
                setattr(c, section, None)
            else:
                lst.pop(i)


def check_memes(c: Content, data: Data, lenient: bool, errors: list[str]) -> None:
    allowed = {str(m.url) for m in data.memes.candidates}
    bad = [u for u in c.memes if str(u) not in allowed]
    for u in bad:
        errors.append(f"memes: {u} is not one of the candidates in data.json")
    if lenient:
        c.memes = [u for u in c.memes if str(u) in allowed]


def check_movers(c: Content, data: Data, edition: str, lenient: bool, errors: list[str]) -> None:
    """Movers must come from the shortlist in data.json (so every number is exact), once each.
    An old-style `standout` story becomes a mover for the top ticker."""
    if not c.movers and c.standout and data.standout.ticker:
        c.movers = [MoverStory(ticker=data.standout.ticker, body=c.standout.body, link=c.standout.link)]
    c.standout = None
    if edition == "weekend" or not data.standout.ok:
        c.movers = []
        return
    known = {m.ticker for m in data.standout.movers} | ({data.standout.ticker} if data.standout.ticker else set())
    keep, seen = [], set()
    for m in c.movers:
        if m.ticker not in known:
            errors.append(f"movers: {m.ticker} is not in data.json's movers shortlist")
        elif m.ticker in seen:
            errors.append(f"movers: {m.ticker} appears twice")
        else:
            keep.append(m)
            seen.add(m.ticker)
    if lenient or len(keep) == len(c.movers):
        c.movers = keep


def check_holdings(c: Content, cfg: dict, lenient: bool, errors: list[str]) -> None:
    holdings = set(cfg["markets"]["holdings"])
    for s in c.holdings_news:
        if s.ticker not in holdings:
            errors.append(f"holdings_news: {s.ticker} is not in config.markets.holdings")
    if lenient:
        c.holdings_news = [s for s in c.holdings_news if s.ticker in holdings]


def data_percents(data: Data) -> list[float]:
    out = []
    m = data.markets
    for q in m.indices + m.crypto + m.holdings:
        out += [q.change_1d_pct, q.wtd_pct, q.ytd_pct]
    out.append(data.standout.change_1d_pct)
    out += [m.change_1d_pct for m in data.standout.movers]
    for r in data.earnings.reported:
        out += [r.revenue_surprise_pct, r.eps_surprise_pct, r.after_hours_pct]
    return [abs(p) for p in out if p is not None]


def check_numbers(c: Content, data: Data, warnings: list[str]) -> None:
    """Flag any % in prose that doesn't match a number in data.json (any rounding)."""
    known = data_percents(data)
    texts = {"intro": c.intro or "", **{f"section_desc.{k}": v for k, v in c.section_desc.items()}}
    if c.big_read:
        texts["big_read"] = c.big_read.body
    for i, s in enumerate(c.top_3):
        texts[f"top_3[{i}]"] = s.body
    for s in c.holdings_news:
        texts[f"holdings {s.ticker}"] = s.body
    for m in c.movers:
        texts[f"movers {m.ticker}"] = m.body
    for where, text in texts.items():
        for n in re.findall(r"(\d+(?:\.\d+)?)\s?(?:%|percent)", text):
            v, dec = float(n), len(n.split(".")[1]) if "." in n else 0
            if not any(round(p, dec) == v for p in known):
                warnings.append(f"{where}: {n}% is not in data.json")


def check_lengths(c: Content, edition: str, warnings: list[str]) -> None:
    if c.big_read and words(c.big_read.body) > CAPS["big_read"]:
        warnings.append(f"big_read is {words(c.big_read.body)} words (cap {CAPS['big_read']})")
    for key, stories in (("top_3", c.top_3), ("holdings", c.holdings_news), ("off_the_clock", c.off_the_clock)):
        for s in stories:
            if words(s.body) > CAPS[key]:
                warnings.append(f'{key}: "{s.headline}" is {words(s.body)} words (cap {CAPS[key]})')
    for k, d in c.section_desc.items():
        if words(d) > CAPS["desc"]:
            warnings.append(f"section_desc.{k} is {words(d)} words; keep it to one line")
    n = len(re.findall(r"[.!?](?:\s|$)", c.intro or ""))
    if c.intro and not 2 <= n <= 5:
        warnings.append(f"intro has {n} sentences (2–5, aim for 3)")
    # Over the length budget: trim from the end of lists first.
    def total():
        t = words(c.intro) + sum(words(v) for v in c.section_desc.values())
        t += sum(words(s.headline) + words(s.body) for s in [c.big_read, *c.top_3, *c.holdings_news, *c.off_the_clock] if s)
        t += sum(words(l.title) for links in c.latest.values() for l in links) + sum(words(l.title) for l in c.your_day_nyc)
        return t
    limit = TRIM_ABOVE.get(edition, 2200)
    for key in ["business", "tech", "world", "pop_culture", "sports"] * 3:
        if total() <= limit:
            break
        if len(c.latest.get(key, [])) > 3:
            dropped = c.latest[key].pop()
            warnings.append(f'over length: trimmed latest.{key} "{dropped.title}"')
    while total() > limit and len(c.off_the_clock) > 2:
        warnings.append(f'over length: trimmed off_the_clock "{c.off_the_clock.pop().headline}"')


# ---------- view model ----------

def split_lead(intro: str) -> tuple[str, str]:
    parts = re.split(r"(?<=[.!?])\s+", (intro or "").strip(), maxsplit=1)
    return parts[0], parts[1] if len(parts) > 1 else ""


def sentences(text: str) -> list[str]:
    """Split at '. ', '? ' or '! ' followed by a capital, digit or quote, but not after an
    abbreviation ("U.S.", "Inc.", "Dr.")."""
    out, start = [], 0
    for m in re.finditer(r"[.!?][\"\u201d\u2019)]?\s+(?=[A-Z0-9\"\u201c$])", text):
        word = text[start:m.start() + 1].split()[-1].rstrip(".").lower() if text[start:m.start() + 1].split() else ""
        if word in ABBREVS or re.fullmatch(r"(?:[a-z]\.)*[a-z]", word):
            continue
        out.append(text[start:m.end()].strip())
        start = m.end()
    out.append(text[start:].strip())
    return [x for x in out if x]


def split_paragraph(text: str, extra: int, limit: int = MAX_PARA_CHARS) -> list[str]:
    """Split one paragraph into even chunks of whole sentences, each at most `limit` characters
    (the first and last chunk share `extra`: an inline headline or link). Never splits a sentence."""
    if len(text) + extra <= limit:
        return [text]
    sents = sentences(text)
    if len(sents) < 2:
        return [text]
    n = -(-(len(text) + extra) // limit)                 # ceil
    target = (len(text) + extra) / n
    chunks, cur = [], ""
    for sent in sents:
        if cur and len(cur) + 1 + len(sent) > target and len(chunks) < n - 1:
            chunks.append(cur)
            cur = sent
        else:
            cur = f"{cur} {sent}" if cur else sent
    chunks.append(cur)
    return chunks


def story_view(s, headline=None, inline=False) -> dict:
    """inline: the headline is the paragraph's first sentence (Big read, Top 3), Morning Brew style.
    The link (article title + ↗) always ends the last paragraph."""
    head = headline or s.headline
    if getattr(s, "emoji", None):
        head = f"{s.emoji} {head}"
    inline_head = head if head.endswith((".", "?", "!")) else head + "."
    link_len = len(s.link.title) + 3
    raw = [p.strip() for p in s.body.split("\n\n") if p.strip()]
    paras = []
    for i, p in enumerate(raw):
        lead = next((l for l in LEAD_INS if p.startswith(l)), None)
        text = p[len(lead):].strip() if lead else p
        extra = (len(lead) + 1 if lead else 0) + (len(inline_head) + 1 if inline and i == 0 else 0) \
            + (link_len if i == len(raw) - 1 else 0)
        for j, chunk in enumerate(split_paragraph(text, extra)):
            paras.append({"lead_in": lead if j == 0 else None, "text": chunk, "head": None, "link": None})
    if not paras:
        paras = [{"lead_in": None, "text": "", "head": None, "link": None}]
    if inline:
        paras[0]["head"] = inline_head
    paras[-1]["link"] = {"title": s.link.title, "url": str(s.link.url)}
    return {"headline": head, "paragraphs": paras, "inline": inline,
            "url": str(s.link.url), "source": s.link.source, "link_title": s.link.title}


def quote_view(q, crypto: bool, period: str) -> dict:
    return {"label": q.label, "price": fmt.price(q.price, crypto),
            "d1": fmt.move(q.change_1d_pct), "period": fmt.move(q.ytd_pct if period == "YTD" else q.wtd_pct)}


def er_cell(actual: str, pct) -> dict:
    return {"actual": actual, "pct": None if pct is None else fmt.signed(pct, 1) + "%", "c": fmt.color(pct, 1)}


def join(*parts) -> str:
    return " ".join(p.strip() for p in parts if p and p.strip())


def your_day_view(data: Data, cal: Calendar | None, c: Content, cfg: dict, edition: str) -> dict:
    rows = []
    w = data.weather
    if w.ok:
        rows.append({"kind": "weather", "icon": w.icon, "temp": f"{w.temp_now}°", "hi": f"H{w.high}°", "lo": f"L{w.low}°",
                     "text": w.outlook or w.conditions or ""})
    if data.mta.ok:
        for a in data.mta.alerts:
            lines = [l for l in cfg["subway_lines"] if l in a.lines]
            rows.append({"kind": "subway", "icon": "subway", "lines": lines, "text": a.text, "detail": None})
    pill = None
    if cal:
        timed = sorted([e for e in cal.today if not e.all_day and e.start], key=lambda e: e.start)
        allday = [e for e in cal.today if e.all_day or not e.start]
        for e in timed + allday:
            if e.kind == "own_birthday":
                pill = "Happy birthday, Wilson!"
                continue
            title = e.title + (" 🎂" if e.kind == "birthday" and "🎂" not in e.title else "")
            rows.append({"kind": "calendar", "icon": "calendar",
                         "left": "All day" if e.all_day or not e.start else fmt.clock(e.start.astimezone(ET)),
                         "text": title, "detail": e.location})
        if edition == "monday" and cal.this_week:
            rows.append({"kind": "header", "text": "This week"})
            for e in sorted(cal.this_week, key=lambda e: (e.start or datetime.min.replace(tzinfo=ET))):
                st = e.start.astimezone(ET) if e.start else None
                rows.append({"kind": "calendar", "icon": "calendar", "left": st.strftime("%a") if st else "",
                             "text": e.title + (" 🎂" if e.kind == "birthday" and "🎂" not in e.title else ""),
                             "detail": "All day" if e.all_day or not st else fmt.clock(st)})
    nyc = [{"title": l.title, "url": str(l.url), "source": l.source} for l in c.your_day_nyc]
    return {"desc": c.section_desc.get("your_day", ""), "rows": rows, "birthday_pill": pill, "nyc": nyc}


def bell_view(data: Data, c: Content, edition: str) -> dict:
    m, cal = data.markets, data.market_calendar
    weekend = edition == "weekend"
    period = "YTD" if edition == "monday" else "WTD"
    closure = cal.closure_line if (cal.ok and not weekend) else None
    if not m.ok:
        return {"label": "Markets" if weekend else "Before the bell", "period_label": period,
                "desc": join("Market data unavailable this morning.", closure), "rows": [], "movers": [],
                "on_deck": [] if weekend else [o.model_dump() for o in c.on_deck_today]}
    rows = [quote_view(q, True, period) for q in m.crypto] if weekend else \
        [quote_view(q, False, period) for q in m.indices] + [quote_view(q, True, period) for q in m.crypto]
    s = data.standout
    pct_of = {m.ticker: m.change_1d_pct for m in s.movers}
    if s.ticker:
        pct_of.setdefault(s.ticker, s.change_1d_pct)
    movers = [{"ticker": m.ticker, "move": fmt.move(pct_of[m.ticker]), **story_view(m, headline=m.ticker)}
              for m in c.movers if m.ticker in pct_of] if (not weekend and s.ok) else []
    return {"label": "Markets" if weekend else "Before the bell", "period_label": period,
            "desc": join(c.section_desc.get("before_the_bell", ""), closure), "rows": rows,
            "movers": movers, "on_deck": [] if weekend else [o.model_dump() for o in c.on_deck_today]}


def earnings_view(data: Data, c: Content, edition: str) -> dict | None:
    if edition == "weekend":
        return None
    e = data.earnings
    if not e.ok:
        return {"desc": "Earnings data unavailable this morning.", "week": [], "reported": []}
    if edition == "monday":
        week = [{"day": d.day, "names": ", ".join(d.names)} for d in e.week]
        return {"desc": c.section_desc.get("earnings", ""), "week": week, "reported": []} if week else None
    if not e.reported:
        return None
    rep = [{"ticker": r.ticker, "revenue": er_cell(fmt.big(r.revenue_actual), r.revenue_surprise_pct),
            "eps": er_cell(fmt.eps(r.eps_actual), r.eps_surprise_pct), "after_hours": fmt.move(r.after_hours_pct)}
           for r in e.reported]
    line = e.next_day.line if e.next_day else None
    return {"desc": join(c.section_desc.get("earnings", ""), line), "week": [], "reported": rep}


def holdings_view(data: Data, c: Content, edition: str) -> dict | None:
    if edition == "weekend":
        return None
    period = "YTD" if edition == "monday" else "WTD"
    m = data.markets
    rows = [quote_view(q, False, period) for q in m.holdings] if m.ok else []
    desc = c.section_desc.get("holdings", "") if m.ok else "Holdings data unavailable this morning."
    return {"desc": desc, "period_label": period, "rows": rows, "stories": [story_view(s) for s in c.holdings_news]}


def latest_view(data: Data, c: Content, edition: str) -> dict | None:
    groups = [{"label": LATEST_LABELS[k], "icon": LATEST_ICONS[LATEST_LABELS[k]], "links": [{"title": l.title, "url": str(l.url), "source": l.source} for l in v]}
              for k, v in c.latest.items() if v]
    card = None
    sp = data.sports
    if sp.ok:
        res = [{"result": g.result, "league": g.league,
                "line": f"{g.team} {g.team_score}, {g.opponent} {g.opponent_score}"} for g in sp.results]
        week = [{"day": g.day, "time": g.time, "line": f"{g.team} {'vs' if g.home else 'at'} {g.opponent}"}
                for g in sp.week] if edition == "monday" else []
        if res or week:
            card = {"results": res, "week": week}
    if not groups and not card:
        return None
    return {"desc": c.section_desc.get("latest", ""), "groups": groups, "sports_card": card}


def memes_view(data: Data, c: Content) -> dict | None:
    if not data.memes.ok or not c.memes:
        return None
    dims = {str(m.url): (m.width, m.height) for m in data.memes.candidates}
    images = []
    for u in c.memes:
        w, h = dims.get(str(u), (None, None))
        images.append({"url": str(u), "height": round(504 * h / w) if w and h else None})
    return {"desc": c.section_desc.get("memes", ""), "images": images}


def build_view(data: Data, cal: Calendar | None, c: Content, cfg: dict, now: datetime) -> dict:
    edition = data.edition
    lead, rest = split_lead(c.intro or "")
    desc = c.section_desc
    v = {
        "brand": cfg["brand"]["name"], "subject": c.subject or f"{cfg['brand']['name']}, {fmt.masthead_date(data.date)}",
        "date_label": fmt.masthead_date(data.date), "lead": lead, "rest": rest, "year": data.date.year,
        "your_day": your_day_view(data, cal, c, cfg, edition),
        "bell": bell_view(data, c, edition),
        "earnings": earnings_view(data, c, edition),
        "holdings": holdings_view(data, c, edition),
        "big_read": {"desc": desc.get("big_read", ""), "story": story_view(c.big_read, inline=True)} if c.big_read else None,
        "top_3": {"desc": desc.get("top_3", ""), "stories": [story_view(s, inline=True) for s in c.top_3]} if c.top_3 else None,
        "latest": latest_view(data, c, edition),
        "off_the_clock": {"desc": desc.get("off_the_clock", ""), "stories": [story_view(s) for s in c.off_the_clock]}
                         if c.off_the_clock else None,
        "memes": memes_view(data, c),
    }
    # Footer: when it was made, and what's missing.
    relevant = [k for k in UNAVAILABLE_NAMES if not (edition == "weekend" and k in ("standout", "earnings"))]
    missing = [UNAVAILABLE_NAMES[k] for k in relevant if not getattr(data, k).ok]
    if cal is None:
        missing.append("Calendar")
    for key, name in (("big_read", "The big read"), ("top_3", "Top 3")):
        if not v[key]:
            missing.append(name)
    t = now.astimezone(ET)
    made = f"Generated {t.hour % 12 or 12}:{t.minute:02d}{'am' if t.hour < 12 else 'pm'} ET."
    v["footer"] = f"{made} All sections delivered." if not missing else f"{made} Unavailable this morning: {', '.join(missing)}."
    v["missing"] = missing
    return v


def check_paragraphs(v: dict, warnings: list[str]) -> None:
    """Warn about any paragraph still over 6 phone lines after splitting (one very long sentence)."""
    stories = list(v["bell"]["movers"])
    stories += (v["holdings"] or {}).get("stories", []) + ([v["big_read"]["story"]] if v["big_read"] else [])
    stories += (v["top_3"] or {}).get("stories", []) + (v["off_the_clock"] or {}).get("stories", [])
    for st in stories:
        for p in st["paragraphs"]:
            n = sum(len(x) + 1 for x in (p.get("head"), p["lead_in"], p["text"]) if x)
            n += len(p["link"]["title"]) + 3 if p.get("link") else 0
            if n > MAX_PARA_CHARS + 30:
                warnings.append(f'"{st["headline"]}": a {n}-character paragraph runs past 6 lines on a phone; '
                                "shorten its sentences")


def icons_used(v: dict) -> list[str]:
    used = {r["icon"] for r in v["your_day"]["rows"] if r.get("icon")}
    if v["latest"]:
        used |= {g["icon"] for g in v["latest"]["groups"]}
        if v["latest"]["sports_card"] and not any(g["label"] == "Sports" for g in v["latest"]["groups"]):
            used.add(LATEST_ICONS["Sports"])
    return sorted(used)


# ---------- rendering ----------

def env() -> Environment:
    e = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True,
                    undefined=StrictUndefined, extensions=["jinja2.ext.do"], keep_trailing_newline=True)
    return e


def render_html(v: dict, icon_src: str) -> str:
    t = env().get_template("email.html.j2")
    html = t.render(v=v, T=tokens.COLORS, D=tokens.DARK, sans=tokens.SANS, mono=tokens.MONO, num=tokens.NUM,
                    section_gap=tokens.SECTION_GAP, content_width=tokens.CONTENT_WIDTH, icon_src=icon_src,
                    arrow=ARROW)
    html = re.sub(r"\n\s*\n+", "\n", html)
    size = len(html.encode())
    if size > MAX_BYTES:
        raise RenderError(f"issue.html is {size:,} bytes, over the {MAX_BYTES:,} limit (Gmail clips). "
                          "Shorten stories, not sections.")
    return html


def render_text(v: dict) -> str:
    e = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=False, undefined=StrictUndefined,
                    trim_blocks=True, lstrip_blocks=True)
    txt = e.get_template("email.txt.j2").render(v=v)
    return re.sub(r"\n{3,}", "\n\n", txt).strip() + "\n"


def render(run_dir: Path, lenient: bool = False, icon_src: str = "cid:{}", now: datetime | None = None,
           out_name: str = "issue", cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    now = now or now_et()
    errors, warnings = [], []
    # Clear the last run's output, so a failed render can never leave a stale issue to send.
    for stale in (f"{out_name}.html", f"{out_name}.txt", "render.json", "render_error.txt"):
        (run_dir / stale).unlink(missing_ok=True)

    data = Data.model_validate(load_json(run_dir / "data.json"))
    raw_cal = load_json(run_dir / "calendar.json")
    try:
        cal = Calendar.model_validate(raw_cal) if raw_cal is not None else None
    except ValidationError as e:
        errors.append(f"calendar.json: {e.error_count()} problems")
        cal = None
    if raw_cal is None:
        warnings.append("calendar.json is missing")

    c = parse_content(load_json(run_dir / "content.json"), lenient, errors)
    if c is None and not lenient:
        raise RenderError("\n".join(errors))
    if c is None:
        c = parse_content({}, True, [])
    if c.edition and c.edition != data.edition:
        warnings.append(f"content.json says edition {c.edition}, data.json says {data.edition}; using data.json")

    check_links(c, cfg, lenient, errors)
    check_memes(c, data, lenient, errors)
    check_holdings(c, cfg, lenient, errors)
    check_movers(c, data, data.edition, lenient, errors)
    if errors and not lenient:
        raise RenderError("\n".join(errors))
    dedupe(c, warnings)
    check_lengths(c, data.edition, warnings)
    check_numbers(c, data, warnings)

    v = build_view(data, cal, c, cfg, now)
    check_paragraphs(v, warnings)
    html = render_html(v, icon_src)
    text = render_text(v)
    (run_dir / f"{out_name}.html").write_text(html)
    (run_dir / f"{out_name}.txt").write_text(text)
    meta = {"subject": v["subject"], "preheader": v["lead"], "icons": icons_used(v), "bytes": len(html.encode()),
            "edition": data.edition, "missing": v["missing"], "warnings": warnings, "errors_dropped": errors}
    (run_dir / "render.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    return meta


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lenient", action="store_true", help="drop invalid items instead of failing")
    p.add_argument("--preview", action="store_true", help="link icons by file path for a browser preview")
    p.add_argument("--run-dir", default=str(RUN_DIR))
    a = p.parse_args()
    src = "../templates/icons/{}.png" if a.preview else "cid:{}"
    try:
        meta = render(Path(a.run_dir), a.lenient, src)
    except Exception as e:
        # brief.send turns this into the plain-text fallback email if nothing renders.
        (Path(a.run_dir) / "render_error.txt").write_text(f"{type(e).__name__}: {e}\n")
        print("render failed:\n" + str(e), file=sys.stderr)
        sys.exit(2)
    for w in meta["warnings"]:
        print("warning:", w)
    for e in meta["errors_dropped"]:
        print("dropped:", e)
    print(f"wrote issue.html ({meta['bytes']:,} bytes) and issue.txt; subject: {meta['subject']}")


if __name__ == "__main__":
    main()
