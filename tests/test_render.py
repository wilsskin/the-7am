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
    assert meta["icons"] == ["calendar", "cloud", "subway"] and 'src="cid:cloud"' in html
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
    assert "Unavailable this morning: Markets, Standout, Earnings, Weather, Meme roundup, Calendar." in html


def test_disallowed_domain_fails_strict_then_drops_lenient(issue):
    def bad(c):
        c["latest"]["tech"][0]["url"] = "https://www.example.com/story"
    with pytest.raises(render.RenderError, match="not an allowed source"):
        go(issue(edit_content=bad))


def test_lenient_drops_disallowed_domain(tmp_path):
    d = tmp_path / "x"
    shutil.copytree(ISSUES / "weekday", d)
    c = json.loads((d / "content.json").read_text())
    c["latest"]["tech"][0]["url"] = "https://www.example.com/story"
    (d / "content.json").write_text(json.dumps(c))
    meta = render.render(d, lenient=True, now=NOW)
    html = (d / "issue.html").read_text()
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


def test_schema_error_strict_fails_lenient_renders(issue):
    def bad(c):
        c["top_3"] = c["top_3"][:2]
        c["subject"] = "x" * 80
    with pytest.raises(render.RenderError):
        go(issue(edit_content=bad))


def test_lenient_keeps_valid_parts(tmp_path):
    d = tmp_path / "x"
    shutil.copytree(ISSUES / "weekday", d)
    c = json.loads((d / "content.json").read_text())
    c["subject"] = "x" * 80
    c["big_read"] = {"headline": "no body or link"}
    (d / "content.json").write_text(json.dumps(c))
    meta = render.render(d, lenient=True, now=NOW)
    html = (d / "issue.html").read_text()
    assert len(meta["subject"]) == 70 and ">The big read</h2>" not in html and ">Top 3</h2>" in html
    assert "The big read" in meta["missing"]


def test_missing_content_still_renders_data_sections(tmp_path):
    d = tmp_path / "x"
    shutil.copytree(ISSUES / "weekday", d)
    (d / "content.json").unlink()
    with pytest.raises(render.RenderError):
        render.render(d, now=NOW)
    meta = render.render(d, lenient=True, now=NOW)
    html = (d / "issue.html").read_text()
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
