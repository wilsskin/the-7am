"""render.py: rules, editions and the email-always-renders promise. Uses the sample issues."""
import json
import shutil
from datetime import datetime
from pathlib import Path

import pytest

from brief import render
from brief.common import ET

ISSUES = Path(__file__).parent / "fixtures" / "issues"
NOW = datetime(2026, 11, 24, 6, 41, tzinfo=ET)


@pytest.fixture
def issue(tmp_path):
    count = iter(range(100))

    def make(name="weekday", edit_content=None, edit_data=None):
        d = tmp_path / f"{name}-{next(count)}"
        shutil.copytree(ISSUES / name, d)
        for fname, fn in (("content.json", edit_content), ("data.json", edit_data)):
            if fn:
                obj = json.loads((d / fname).read_text())
                fn(obj)
                (d / fname).write_text(json.dumps(obj))
        return d
    return make


def go(d, **kw):
    meta = render.render(d, now=NOW, **kw)
    return meta, (d / "issue.html").read_text(), (d / "issue.txt").read_text()


@pytest.mark.parametrize("name", ["weekday", "monday", "weekend", "birthday", "unavailable"])
def test_every_sample_renders_under_the_size_limit(issue, name):
    meta, html, txt = go(issue(name), lenient=True)
    assert meta["bytes"] < render.MAX_BYTES and "<html" in html and "Wilson Skinner" in txt


def test_weekday_has_code_owned_sentences(issue):
    meta, html, txt = go(issue())
    assert "Chips led a down day for the Nasdaq. Markets close Thursday for Thanksgiving, early close Friday at 1pm." in html
    assert "Walmart missed on revenue. Deere reports tomorrow." in html
    assert "NVDA <span" in html and "−6.40%" in html
    assert "57.0B" in html and "(+3.3%)" in html and "(−0.3%)" in html
    assert ">WTD<" in html and ">YTD<" not in html
    assert meta["icons"] == ["calendar", "cloud", "subway", "tag-business", "tag-pop", "tag-sports", "tag-tech", "tag-world"] and 'src="cid:cloud"' in html
    assert "All sections delivered." in html


def test_monday_ytd_week_calendar_and_games(issue):
    meta, html, _ = go(issue("monday"))
    assert ">YTD<" in html and "Reporting this week" in html and "Reported yesterday" not in html
    assert "Dell Technologies, Salesforce" in html and "Warriors vs Rockets" in html
    assert html.count("This week") == 2          # calendar card and sports card


def test_weekend_drops_equities(issue):
    _, html, _ = go(issue("weekend"))
    assert ">Markets<" in html and "S&amp;P 500" not in html and "Bitcoin" in html
    assert "Earnings" not in html and "Your holdings" not in html and "On deck today" not in html


def test_own_birthday_pill(issue):
    _, html, _ = go(issue("birthday"))
    assert "Happy birthday, Wilson!" in html and 'class="tpill"' in html and "Happy birthday!</span>" not in html


def test_unavailable_states(issue):
    meta, html, _ = go(issue("unavailable"), lenient=True)
    assert "Market data unavailable this morning." in html
    assert "Earnings data unavailable this morning." in html
    assert "Holdings data unavailable this morning." in html
    assert "Meme roundup" not in html.split("Unavailable this morning")[0]   # section skipped entirely
    assert "Unavailable this morning: Markets, Big movers, Earnings, Weather, Meme roundup, Calendar." in html


def test_disallowed_domain_fails_strict_then_drops_lenient(issue):
    def bad(c):
        c["latest"]["tech"][0]["url"] = "https://www.example.com/story"
    with pytest.raises(render.RenderError, match="not an allowed source"):
        go(issue(edit_content=bad))
    meta, html, _ = go(issue(edit_content=bad), lenient=True)
    assert "example.com" not in html and "Sample headline about big tech regulation" in html
    assert meta["errors_dropped"]


def test_meme_must_be_a_candidate(issue):
    def bad(c):
        c["memes"][0] = "https://i.redd.it/not-a-candidate.jpg"
    with pytest.raises(render.RenderError, match="not one of the candidates"):
        go(issue(edit_content=bad))


def test_unknown_holding_ticker(issue):
    def bad(c):
        c["holdings_news"][0]["ticker"] = "TSLA"
        c["holdings_news"][0]["headline"] = "TSLA: Something happened"
    with pytest.raises(render.RenderError, match="TSLA is not in config"):
        go(issue(edit_content=bad))


def test_schema_error_strict_fails_lenient_keeps_valid_parts(issue):
    def bad(c):
        c["subject"] = "x" * 80
        c["big_read"] = {"headline": "no body or link"}
    with pytest.raises(render.RenderError):
        go(issue(edit_content=bad))
    meta, html, _ = go(issue(edit_content=bad), lenient=True)
    assert len(meta["subject"]) == 70 and ">The big read</h2>" not in html and ">Top 3</h2>" in html
    assert "The big read" in meta["missing"]


def test_lenient_drops_only_the_bad_link_or_description(issue):
    def bad(c):
        c["latest"]["tech"][0]["url"] = "not a url"
        c["section_desc"]["movers"] = "not a section"
    meta, html, _ = go(issue(edit_content=bad), lenient=True)
    tech = json.loads((ISSUES / "weekday" / "content.json").read_text())["latest"]["tech"]
    assert tech[0]["title"] not in html and tech[1]["title"] in html and ">The latest</h2>" in html
    assert "Chips led a down day for the Nasdaq." in html     # the other descriptions survive


def test_missing_content_still_renders_data_sections(issue):
    d = issue()
    (d / "content.json").unlink()
    with pytest.raises(render.RenderError):
        render.render(d, now=NOW)
    _, html, _ = go(d, lenient=True)
    assert "S&amp;P 500" in html and "Before the bell" in html


def test_duplicate_url_dropped_from_lower_priority(issue):
    def dup(c):
        c["latest"]["business"][0]["url"] = c["top_3"][0]["link"]["url"]
    meta, html, _ = go(issue(edit_content=dup))
    assert "Sample headline about a deal or Wall Street move" not in html
    assert any("dropped duplicate" in w for w in meta["warnings"])


def test_percent_not_in_data_is_flagged(issue):
    def pct(c):
        c["intro"] = "Nvidia fell 12.5% after hours. Then it bounced. Then it fell again."
    meta, _, _ = go(issue(edit_content=pct))
    assert any("12.5% is not in data.json" in w for w in meta["warnings"])
    def ok(c):
        c["intro"] = "Nvidia fell 6.4% after hours. Then it bounced. Then it fell again."
    meta, _, _ = go(issue(edit_content=ok))
    assert not any("is not in data.json" in w for w in meta["warnings"])


def test_similar_headlines():
    assert render.similar("Nvidia beats estimates, stock falls after hours", "Nvidia beats estimates and stock falls after hours")
    assert not render.similar("Sample story one headline with a verb", "Sample story two headline with a verb")
    assert not render.similar("Nvidia rises on earnings", "Nvidia falls on earnings")


def test_too_big_fails_loudly(issue):
    def huge(c):
        c["big_read"]["body"] = "\n\n".join(["word " * 300] * 30)
    with pytest.raises(render.RenderError, match="Gmail clips"):
        go(issue(edit_content=huge))


def test_leisure_sources_only_in_off_the_clock(issue):
    def ok(c):
        c["off_the_clock"][0]["link"]["url"] = "https://www.killington.com/mountain-report"
    go(issue(edit_content=ok))
    def bad(c):
        c["latest"]["tech"][0]["url"] = "https://www.timeout.com/newyork/things-to-do"
    with pytest.raises(render.RenderError, match="not an allowed source"):
        go(issue(edit_content=bad))


def test_long_paragraph_splits_at_a_sentence_break():
    text = ("Nvidia beat on revenue and earnings. The U.S. government cleared new chip exports to the Gulf. "
            "Shares still fell after hours as investors worried about margins. Analysts at Goldman kept their "
            "buy rating. The company guided above the street for next quarter. Inc. filings come Friday.")
    chunks = render.split_paragraph(text, 0)
    assert len(chunks) == 2 and all(len(c) <= render.MAX_PARA_CHARS for c in chunks)
    assert " ".join(chunks) == text
    assert not any(c.endswith("U.S.") for c in chunks)
    assert render.split_paragraph("Short one.", 0) == ["Short one."]


def test_movers_render_and_must_come_from_the_shortlist(issue):
    meta, html, _ = go(issue())
    assert "NVDA <span" in html and "WMT <span" in html and "AVGO <span" in html and "+4.12%" in html

    def bad(c):
        c["movers"][1]["ticker"] = "TSLA"
    with pytest.raises(render.RenderError, match="TSLA is not in data.json's movers shortlist"):
        go(issue(edit_content=bad))
    meta, html, _ = go(issue(edit_content=bad), lenient=True)
    assert "TSLA <span" not in html and "NVDA <span" in html


def test_plain_text_keeps_lead_ins_and_paragraphs_in_every_section(issue):
    def lead(c):
        for s in (c["top_3"][0], c["movers"][0], c["off_the_clock"][0]):
            s["body"] = "First paragraph here.\n\nWhy it matters: second paragraph here."
    _, _, txt = go(issue(edit_content=lead))
    assert txt.count("Why it matters: second paragraph here.") == 3
    assert txt.count("First paragraph here.\n\nWhy it matters:") == 3


def test_emoji_before_headline_and_bad_emoji_rejected(issue):
    meta, html, _ = go(issue())
    assert "⛷️ Ski report: Killington" in html and "🏦 Sample story one headline with a verb." in html

    def bad(c):
        c["top_3"][0]["emoji"] = "ski"
    with pytest.raises(render.RenderError):
        go(issue(edit_content=bad))


def test_six_memes_from_mixed_sources(issue):
    beehiiv = "https://media.beehiiv.com/cdn-cgi/image/fit=scale-down,format=auto,quality=80,width=1008,onerror=redirect/uploads/asset/file/m{}/image.png"
    urls = [beehiiv.format(i) for i in range(5)] + ["https://lemmy.world/pictrs/image/a.webp"]

    def data(d):
        d["memes"]["candidates"] = [{"url": u, "title": "", "community": "Short Squeez", "score": None,
                                     "permalink": "https://www.shortsqueez.co/p/x", "width": 1206 if i < 4 else None,
                                     "height": 1511 if i < 4 else None} for i, u in enumerate(urls)]

    def content(c):
        c["memes"] = urls
    meta, html, _ = go(issue(edit_data=data, edit_content=content))
    assert html.count('alt="Meme"') == 6
    assert 'height="631"' in html          # 504 * 1511 / 1206, when the size is known
    assert "width=1008" in html and "lemmy.world/pictrs/image/a.webp" in html


def test_story_links_read_as_the_outlet_not_the_article_title(issue):
    def titled(c):
        c["top_3"][0]["link"]["title"] = "An article title nobody should see"
    meta, html, txt = go(issue(edit_content=titled))
    src = json.loads((ISSUES / "weekday" / "content.json").read_text())["top_3"][0]["link"]["source"]
    assert "An article title nobody should see" not in html and "An article title nobody should see" not in txt
    assert f'white-space:nowrap;">{src}&nbsp;' in html


def test_on_deck_runs_in_time_order_with_all_day_items_last(issue):
    def deck(c):
        c["on_deck_today"] = [{"time": None, "text": "Black Friday"}, {"time": "2:00", "text": "Fed minutes"},
                              {"time": "10:00", "text": "Consumer sentiment"}, {"time": "8:30", "text": "Jobless claims"}]
    _, html, txt = go(issue(edit_content=deck))
    order = [html.index(t) for t in ("Jobless claims", "Consumer sentiment", "Fed minutes", "Black Friday")]
    assert order == sorted(order)
    assert "–  Black Friday" in txt and "2:00  Fed minutes" in txt


def test_on_deck_time_parsing():
    m = render.on_deck_minutes
    assert m("8:30") == 510 and m("2:00") == 840 and m("12:00") == 720 and m("2:00pm") == 840
    assert m("11:30am") == 690 and m(None) is None and m("All day") is None


def test_card_order_follows_config(issue):
    _, html, _ = go(issue())
    assert html.index(">S&amp;P 500<") < html.index(">Nasdaq<") < html.index(">Dow<")
    pos = [html.index(f">{t}</span>") for t in ("SOXX", "PLTR", "GOOGL", "GEV", "COST", "V", "GS")]
    assert pos == sorted(pos)


# ---------- no repeats from the last issues (Wilson, Nov 27, 2026) ----------

def write_previous(d, body, day="2026-11-23", subject="Yesterday's issue"):
    (d / "previous.json").write_text(json.dumps([{"id": "x", "date": day, "subject": subject, "body": body}]))


def test_repeat_link_or_headline_fails_strict_and_drops_lenient(issue):
    d = issue()
    c = json.loads((d / "content.json").read_text())
    old_link = c["latest"]["tech"][0]
    old_head = c["top_3"][2]["headline"]
    write_previous(d, f"The 7AM · Mon Nov 23\n\n- Some other wording ({old_link['source']}) {old_link['url']}\n\n"
                      f"🌍 {old_head}. Placeholder text.\n")
    with pytest.raises(render.RenderError, match="already in 2026-11-23"):
        render.render(d, now=NOW)
    meta = render.render(d, lenient=True, now=NOW)
    html = (d / "issue.html").read_text()
    assert old_link["title"] not in html and old_head not in html
    assert sum("Replace it with fresh news" in e for e in meta["errors_dropped"]) == 2


def test_reworded_repeat_is_a_warning(issue):
    def ski(c):
        c["off_the_clock"][0]["headline"] = "Ski report: Killington hosts the World Cup this weekend"
    d = issue(edit_content=ski)
    write_previous(d, "The 7AM · Mon Nov 23\n\n⛷️ Ski report: Killington gets the green light for World Cup weekend\n")
    meta = render.render(d, now=NOW)
    assert any("may repeat" in w and "Killington" in w for w in meta["warnings"])


def test_previous_ignores_today_and_non_issues(issue):
    d = issue()
    c = json.loads((d / "content.json").read_text())
    url = c["latest"]["tech"][0]["url"]
    (d / "previous.json").write_text(json.dumps([
        {"date": "2026-11-24", "subject": "today's test send", "body": f"The 7AM · Tue Nov 24\n- x (NYT) {url}\n"},
        {"date": "2026-11-23", "subject": "not an issue", "body": f"Some other email {url}\n"}]))
    render.render(d, now=NOW)
    assert c["latest"]["tech"][0]["title"] in (d / "issue.html").read_text()


def test_no_previous_file_is_fine(issue):
    meta = render.render(issue(), now=NOW)
    assert not any("repeat" in w for w in meta["warnings"])


def test_reminders_due_on_countdown_days_only():
    from datetime import date
    cfg = {"reminders": [{"date": date(2027, 3, 14), "days_before": [14, 7, 3, 2, 1], "text": "Move the cron."}]}
    due = lambda d: render.reminders_due(cfg, d)
    assert due(date(2027, 2, 28)) == ["Reminder. In 2 weeks: Move the cron."]
    assert due(date(2027, 3, 7)) == ["Reminder. In 1 week: Move the cron."]
    assert due(date(2027, 3, 11)) == ["Reminder. In 3 days: Move the cron."]
    assert due(date(2027, 3, 13)) == ["Reminder. Tomorrow: Move the cron."]
    assert due(date(2027, 2, 23)) == [] and due(date(2027, 3, 14)) == [] and render.reminders_due({}, date(2027, 3, 13)) == []
