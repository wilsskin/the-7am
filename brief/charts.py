"""python -m brief.charts            fetch and draw the charts requested in run/content.json
python -m brief.charts --search "fed december"   find Kalshi / Polymarket markets to chart

Charts are supporting evidence for a story, never forced (Wilson, Nov 27, 2026). Claude
decides each morning whether a story deserves one and adds a `chart` request to it in
content.json: which free source, which series or market, and a title. This module fetches
the exact numbers from that source and draws a PNG, so Claude never writes a chart number.

Sources (all free, no key):
  kalshi      event ticker, e.g. KXFEDDECISION-26DEC     odds now, or how they moved
  polymarket  event slug, e.g. fed-decisions-dec-mar     odds now, or how they moved
  bls         series id, e.g. CUUR0000SA0 (CPI)          level, yoy % or monthly change
  yahoo       symbol, e.g. ^TNX (10-year yield), CL=F    daily close

Writes run/charts/<key>.png and run/charts.json. A chart that fails is marked ok: false
and its story renders without it. The email always sends.
"""
import argparse
import json
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

from brief import tokens
from brief.common import ET, RUN_DIR, TIMEOUT, USER_AGENT, get_json, now_et
from brief.schema import ChartRequest, Content

MAX_CHARTS = 3                      # per issue; most days have none
KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
POLY_GAMMA = "https://gamma-api.polymarket.com"
POLY_CLOB = "https://clob.polymarket.com"
BLS = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
PERIOD_DAYS = {"1m": 31, "3m": 92, "6m": 183, "1y": 366, "2y": 731, "5y": 1827}
SOURCE_LABEL = {"kalshi": "Kalshi", "polymarket": "Polymarket", "bls": "BLS", "yahoo": "Yahoo Finance"}
RATE_SYMBOLS = {"^TNX", "^IRX", "^FVX", "^TYX"}   # Yahoo quotes these as a yield in percent
MAX_ODDS_BARS = 6
MAX_LINES = 3


# ---------- which stories asked for a chart ----------

def requests_in(c: Content) -> list[tuple[str, ChartRequest]]:
    """(where, request) in placement priority, capped at MAX_CHARTS. `where` matches render.py."""
    out = []
    if c.big_read and c.big_read.chart:
        out.append(("big_read", c.big_read.chart))
    out += [(f"top_3[{i}]", s.chart) for i, s in enumerate(c.top_3) if s.chart]
    out += [(f"holdings[{s.ticker}]", s.chart) for s in c.holdings_news if s.chart]
    out += [(f"movers[{m.ticker}]", m.chart) for m in c.movers if m.chart]
    return out[:MAX_CHARTS]


# ---------- fetching (network) ----------
# Each returns {"kind": "bars"|"lines", "unit": "%"|"", "bars": [(label, value)],
#               "x": [date], "lines": [{"name", "values"}]}

def _prob(m: dict, *keys) -> float | None:
    for k in keys:
        v = m.get(k)
        if v not in (None, ""):
            v = float(v)
            return v * 100 if v <= 1 else v
    return None


def fetch_kalshi(req: ChartRequest, now: datetime) -> dict:
    ev = get_json(f"{KALSHI}/events/{req.id}", params={"with_nested_markets": "true"})
    event = ev.get("event") or {}
    markets = ev.get("markets") or event.get("markets") or []
    if not markets:
        raise RuntimeError(f"Kalshi event {req.id} has no markets")
    outcomes = []
    for m in markets:
        p = _prob(m, "last_price_dollars", "previous_price_dollars")
        if p is None:
            bid, ask = _prob(m, "yes_bid_dollars"), _prob(m, "yes_ask_dollars")
            p = (bid + ask) / 2 if bid is not None and ask is not None else None
        if p is not None:
            outcomes.append((m.get("yes_sub_title") or m.get("title") or m["ticker"], round(p), m["ticker"]))
    outcomes.sort(key=lambda o: -o[1])
    if req.view == "odds":
        return {"kind": "bars", "unit": "%", "bars": [(n, v) for n, v, _ in outcomes[:MAX_ODDS_BARS]]}
    series = event.get("series_ticker") or req.id.split("-")[0]
    end = int(now.timestamp())
    start = end - PERIOD_DAYS[req.period] * 86400
    lines, xs = [], None
    for name, _, ticker in outcomes[:MAX_LINES]:
        cs = get_json(f"{KALSHI}/series/{series}/markets/{ticker}/candlesticks",
                      params={"start_ts": start, "end_ts": end, "period_interval": 1440}).get("candlesticks", [])
        pts = {datetime.fromtimestamp(c["end_period_ts"], ET).date(): float(c["price"]["close_dollars"]) * 100
               for c in cs if (c.get("price") or {}).get("close_dollars") is not None}
        if pts:
            lines.append((name, pts))
    return _align(lines)


def fetch_polymarket(req: ChartRequest, now: datetime) -> dict:
    events = get_json(f"{POLY_GAMMA}/events", params={"slug": req.id})
    if not events:
        raise RuntimeError(f"Polymarket event {req.id} not found")
    outcomes = []
    for m in events[0].get("markets", []):
        if m.get("closed"):
            continue
        prices = json.loads(m.get("outcomePrices") or "[]")
        tokens_ = json.loads(m.get("clobTokenIds") or "[]")
        names = json.loads(m.get("outcomes") or '["Yes","No"]')
        if len(events[0].get("markets", [])) == 1:          # one yes/no market: chart both sides
            outcomes += [(names[i], float(prices[i]) * 100, tokens_[i]) for i in range(min(len(prices), len(tokens_)))]
        elif prices and tokens_:
            outcomes.append((m.get("groupItemTitle") or m.get("question"), float(prices[0]) * 100, tokens_[0]))
    if not outcomes:
        raise RuntimeError(f"Polymarket event {req.id} has no open markets")
    outcomes.sort(key=lambda o: -o[1])
    if req.view == "odds":
        return {"kind": "bars", "unit": "%", "bars": [(n, round(v)) for n, v, _ in outcomes[:MAX_ODDS_BARS]]}
    start = int(now.timestamp()) - PERIOD_DAYS[req.period] * 86400
    lines = []
    for name, _, tok in outcomes[:MAX_LINES if len(outcomes) > 2 else 1]:
        hist = get_json(f"{POLY_CLOB}/prices-history",
                        params={"market": tok, "startTs": start, "fidelity": 1440}).get("history", [])
        pts = {datetime.fromtimestamp(h["t"], ET).date(): float(h["p"]) * 100 for h in hist}
        if pts:
            lines.append((name, pts))
    return _align(lines)


def fetch_bls(req: ChartRequest, now: datetime) -> dict:
    years = PERIOD_DAYS[req.period] // 365 + 2              # one extra year for yoy
    body = {"seriesid": [req.id], "startyear": str(now.year - years), "endyear": str(now.year)}
    r = requests.post(BLS, json=body, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    d = r.json()
    if d.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(f"BLS: {d.get('status')} {d.get('message')}")
    rows = d["Results"]["series"][0]["data"]
    pts = sorted((date(int(x["year"]), int(x["period"][1:]), 1), float(x["value"]))
                 for x in rows if x["period"].startswith("M") and x["period"] != "M13" and x["value"] not in ("-", ""))
    vals = dict(pts)
    out = {}
    for dt, v in pts:
        if req.transform == "yoy":
            base = vals.get(date(dt.year - 1, dt.month, 1))
            if base:
                out[dt] = round((v / base - 1) * 100, 1)
        elif req.transform == "mom":
            prev = vals.get(date(dt.year - (dt.month == 1), (dt.month - 2) % 12 + 1, 1))
            if prev is not None:
                out[dt] = round(v - prev, 1)
        else:
            out[dt] = v
    cut = now.date() - timedelta(days=PERIOD_DAYS[req.period])
    out = {k: v for k, v in out.items() if k >= cut.replace(day=1)}
    unit = "%" if req.transform == "yoy" else ""
    return {**_align([(req.id, out)]), "unit": unit, "monthly": True,
            "bar_change": req.transform == "mom"}


def fetch_yahoo(req: ChartRequest, now: datetime) -> dict:
    from brief.collect.markets import fetch_daily_closes
    start = now.date() - timedelta(days=PERIOD_DAYS[req.period])
    closes = fetch_daily_closes([req.id], start, now.date())[req.id]
    if not closes:
        raise RuntimeError(f"Yahoo returned nothing for {req.id}")
    return {**_align([(req.id, {k: round(v, 2) for k, v in closes.items()})]),
            "unit": "%" if req.id in RATE_SYMBOLS else ""}


FETCHERS = {"kalshi": fetch_kalshi, "polymarket": fetch_polymarket, "bls": fetch_bls, "yahoo": fetch_yahoo}


def _align(lines: list[tuple[str, dict]]) -> dict:
    """Put every line on the same dates (the first line's), carrying values forward."""
    if not lines:
        raise RuntimeError("no history returned")
    xs = sorted(set().union(*(pts.keys() for _, pts in lines)))
    out = []
    for name, pts in lines:
        last, vals = None, []
        for x in xs:
            last = pts.get(x, last)
            vals.append(None if last is None else round(last, 2))
        out.append({"name": name, "values": vals})
    return {"kind": "lines", "unit": "%", "x": xs, "lines": out}


# ---------- drawing (pure, tested) ----------

def fmt_value(v: float, unit: str) -> str:
    """72%, 3.1%, 4.25, 119, 6,812. Real minus sign, like the rest of the issue."""
    a = abs(v)
    if a >= 100 or (unit == "%" and a >= 10):
        s = f"{a:,.0f}"
    elif unit == "%":
        s = f"{a:.1f}".rstrip("0").rstrip(".")
    else:
        s = f"{a:.2f}".rstrip("0").rstrip(".")
    return ("−" if round(v, 2) < 0 else "") + s + unit


def numbers(series: dict) -> list[float]:
    """Every value printed on the chart, so render.py's number check knows them."""
    if series["kind"] == "bars":
        return [v for _, v in series["bars"]]
    return [l["values"][-1] for l in series["lines"] if l["values"] and l["values"][-1] is not None]


def alt_text(title: str, source: str, series: dict) -> str:
    """What the chart says, for images-off and screen readers."""
    u = series["unit"]
    if series["kind"] == "bars":
        parts = [f"{n} {fmt_value(v, u)}" for n, v in series["bars"]]
    else:
        end = series["x"][-1].strftime("%b %Y" if series.get("monthly") else "%b %-d")
        parts = [(f"{l['name']} " if len(series["lines"]) > 1 else "") + f"{fmt_value(l['values'][-1], u)} as of {end}"
                 for l in series["lines"] if l["values"] and l["values"][-1] is not None]
    return f"Chart: {title}. " + "; ".join(parts) + f". Source: {source}."


def draw(series: dict, path: Path) -> tuple[int, int]:
    """A quiet chart in the design system's grays, drawn at 2x for a 504px column.
    Returns the size to show it at (504 wide)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    from matplotlib import font_manager
    from PIL import Image

    C = tokens.COLORS
    # The system font where there is one (Mac); the cloud task runs Linux, which falls back.
    have = {f.name for f in font_manager.fontManager.ttflist}
    fonts = [f for f in ("SF Pro Text", "Helvetica Neue", "Helvetica", "Arial", "Liberation Sans") if f in have]
    plt.rcParams.update({"font.family": fonts + ["DejaVu Sans"], "font.size": 12, "axes.unicode_minus": True})
    lines = series["kind"] == "lines"
    # Text sits outside the plot area (axis labels, end labels), and savefig trims to it,
    # so the plot is drawn a bit narrower than the 504px column and the PNG fits the text.
    right = 0.62 if lines and len(series["lines"]) > 1 else 0.86
    fig = plt.figure(figsize=(5.04, 2.6 if lines else 0.3 + 0.38 * len(series["bars"])), dpi=200)
    fig.patch.set_facecolor(C["surface"])
    ax = fig.add_axes([0.1, 0.1, right - 0.1, 0.85] if lines else [0.3, 0.02, 0.6, 0.96])
    ax.set_facecolor(C["surface"])
    for s in ax.spines.values():
        s.set_visible(False)
    u = series["unit"]

    if series["kind"] == "bars":
        names = [n for n, _ in series["bars"]][::-1]
        vals = [v for _, v in series["bars"]][::-1]
        colors = [C["secondary"]] * (len(vals) - 1) + [C["primary"]]
        ax.barh(range(len(vals)), vals, height=0.56, color=colors)
        ax.set_xlim(0, 100 if u == "%" else max(vals) * 1.25)
        ax.set_xticks([])
        ax.set_yticks(range(len(vals)), names, color=C["primary"], fontsize=12)
        ax.tick_params(axis="y", length=0, pad=6)
        for i, v in enumerate(vals):
            ax.text(v + (ax.get_xlim()[1] * 0.015), i, fmt_value(v, u), va="center", fontsize=12,
                    color=C["primary"] if i == len(vals) - 1 else C["secondary"])
    else:
        xs = series["x"]
        styles = [(C["primary"], "-", 2.0), (C["secondary"], "-", 1.6), (C["secondary"], (0, (4, 3)), 1.6)]
        many = len(series["lines"]) > 1
        if series.get("bar_change"):
            v = series["lines"][0]["values"]
            ax.bar(xs, v, width=20, color=[C["primary"] if (x or 0) >= 0 else C["secondary"] for x in v])
            ax.axhline(0, color=C["secondary"], linewidth=0.8)
        else:
            for (color, ls, lw), l in zip(styles, series["lines"]):
                ax.plot(xs, l["values"], color=color, linestyle=ls, linewidth=lw, solid_capstyle="round")
        # Label each line's last value at its end, so there's no legend to decode.
        ends = []
        for (color, _, _), l in zip(styles, series["lines"]):
            last = next((v for v in reversed(l["values"]) if v is not None), None)
            if last is not None:
                ends.append([last, color, (f"{l['name']} " if many else "") + fmt_value(last, u)])
        lo, hi = ax.get_ylim()
        gap = (hi - lo) * 0.09
        ends.sort(key=lambda e: e[0])
        for i in range(1, len(ends)):                       # keep end labels from overlapping
            ends[i][0] = max(ends[i][0], ends[i - 1][0] + gap)
        for y, color, text in ends:
            ax.annotate(text, xy=(1, y), xycoords=("axes fraction", "data"), xytext=(6, 0),
                        textcoords="offset points", va="center", fontsize=12, color=color)
        ax.yaxis.set_major_locator(plt.MaxNLocator(4))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: fmt_value(v, u)))
        ax.grid(axis="y", color=C["bg"], linewidth=1.2)        # page color on the card: light, quiet lines
        ax.set_axisbelow(True)
        span = (xs[-1] - xs[0]).days if len(xs) > 1 else 0
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=5))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y" if span > 300 else "%b %-d"))
        ax.tick_params(colors=C["secondary"], labelsize=11, length=0, pad=4)
        ax.margins(x=0.01)
    fig.savefig(path, dpi=200, facecolor=C["surface"], bbox_inches="tight", pad_inches=0.16)
    plt.close(fig)
    with Image.open(path) as im:
        w, h = im.size
    return 504, round(504 * h / w)                     # shown at the column width, 2x pixels


# ---------- run ----------

def make(req: ChartRequest, key: str, out_dir: Path, now: datetime, fetch=None) -> dict:
    label = SOURCE_LABEL[req.source]
    base = {"key": key, "source": req.source, "id": req.id, "title": req.title, "source_label": label}
    try:
        series = (fetch or FETCHERS[req.source])(req, now)
        if req.unit is not None:
            series["unit"] = req.unit
        if series["kind"] == "lines" and not any(v is not None for l in series["lines"] for v in l["values"]):
            raise RuntimeError("no data points")
        out_dir.mkdir(parents=True, exist_ok=True)
        w, h = draw(series, out_dir / f"{key}.png")
        return {**base, "ok": True, "file": f"charts/{key}.png", "width": w, "height": h,
                "as_of": now.isoformat(), "alt": alt_text(req.title, label, series), "numbers": numbers(series)}
    except Exception as e:
        return {**base, "ok": False, "error": f"{type(e).__name__}: {e}"}


def run(run_dir: Path, now: datetime | None = None) -> list[dict]:
    now = now or now_et()
    c = Content.model_validate(json.loads((run_dir / "content.json").read_text()))
    out_dir = run_dir / "charts"
    for old in out_dir.glob("*.png") if out_dir.exists() else []:
        old.unlink()
    charts = []
    for i, (where, req) in enumerate(requests_in(c), 1):
        charts.append({"where": where, **make(req, f"chart{i}", out_dir, now)})
    (run_dir / "charts.json").write_text(json.dumps({"charts": charts}, indent=2, ensure_ascii=False))
    return charts


def search(q: str) -> None:
    """Print open Kalshi and Polymarket markets matching q, to pick a chart id from."""
    words = q.lower().split()
    try:
        d = get_json(f"{POLY_GAMMA}/public-search", params={"q": q, "limit_per_type": 8})
        for e in d.get("events", []):
            if not e.get("closed"):
                print(f"polymarket  {e['slug']}  |  {e['title']}")
    except Exception as e:
        print(f"polymarket search failed: {e}")
    try:
        series = get_json(f"{KALSHI}/series").get("series", [])
        hits = [s for s in series if all(w in (s.get("title", "") + " " + s["ticker"]).lower() for w in words)][:6]
        for s in hits:
            evs = get_json(f"{KALSHI}/events", params={"series_ticker": s["ticker"], "status": "open", "limit": 4})
            for e in evs.get("events", []):
                print(f"kalshi      {e['event_ticker']}  |  {e['title']} {e.get('sub_title') or ''}".rstrip())
            time.sleep(0.2)
    except Exception as e:
        print(f"kalshi search failed: {e}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--search", help="find Kalshi / Polymarket markets matching these words")
    p.add_argument("--run-dir", default=str(RUN_DIR))
    a = p.parse_args()
    if a.search:
        search(a.search)
        return
    charts = run(Path(a.run_dir))
    if not charts:
        print("no charts requested")
    for ch in charts:
        status = f"{ch['file']}  ({ch['alt']})" if ch["ok"] else f"FAILED: {ch['error']}"
        print(f"{ch['key']} for {ch['where']}: {status}")


if __name__ == "__main__":
    main()
