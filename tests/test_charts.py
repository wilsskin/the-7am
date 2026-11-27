"""brief/charts.py: supporting charts. Network calls are faked; drawing is real (matplotlib)."""
import json
import shutil
from datetime import date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from brief import charts, render, send
from brief.common import ET
from brief.schema import ChartRequest, Content

ISSUES = Path(__file__).parent / "fixtures" / "issues"
NOW = datetime(2026, 11, 24, 6, 41, tzinfo=ET)


def copy_weekday(tmp_path, edit=None):
    d = tmp_path / "weekday"
    shutil.copytree(ISSUES / "weekday", d)
    if edit:
        obj = json.loads((d / "charts.json").read_text())
        edit(obj["charts"][0])
        (d / "charts.json").write_text(json.dumps(obj))
    return d


def test_chart_renders_under_its_story_and_is_attached(tmp_path):
    d = copy_weekday(tmp_path)
    meta = render.render(d, now=NOW)
    html, txt = (d / "issue.html").read_text(), (d / "issue.txt").read_text()
    assert 'src="cid:chart1"' in html and "Inflation, year over year" in html and "Source: BLS" in html
    assert 'alt="Chart: Inflation, year over year. 3.7% as of Oct 2026. Source: BLS."' in html
    assert html.index("Sample story two") < html.index("cid:chart1") < html.index("Sample story three")
    assert meta["charts"] == [{"cid": "chart1", "file": "charts/chart1.png"}]
    assert "Chart: Inflation, year over year. 3.7%" in txt
    att = send.attachments(meta["icons"], meta["charts"], d)
    assert [a["content_id"] for a in att][-1] == "chart1" and all(a["content"] for a in att)


def test_chart_numbers_count_as_known(tmp_path):
    d = copy_weekday(tmp_path)
    c = json.loads((d / "content.json").read_text())
    c["top_3"][1]["body"] = "Inflation ran 3.7% over the past year. That is above the Fed's goal."
    (d / "content.json").write_text(json.dumps(c))
    meta = render.render(d, now=NOW)
    assert not any("3.7%" in w for w in meta["warnings"])


@pytest.mark.parametrize("change", [lambda ch: ch.update(ok=False, error="BLS: down"),
                                    lambda ch: ch.update(id="SOMETHING_ELSE"),
                                    lambda ch: ch.update(file="charts/missing.png")])
def test_failed_or_mismatched_chart_is_left_out_and_the_story_stays(tmp_path, change):
    d = copy_weekday(tmp_path, change)
    meta = render.render(d, now=NOW)
    html = (d / "issue.html").read_text()
    assert "cid:chart" not in html and "Sample story two" in html and meta["charts"] == []


def test_no_charts_json_is_fine(tmp_path):
    d = copy_weekday(tmp_path)
    (d / "charts.json").unlink()
    meta = render.render(d, now=NOW)
    assert meta["charts"] == [] and "Sample story two" in (d / "issue.html").read_text()


def test_requests_are_capped_and_in_priority_order():
    c = Content.model_validate(json.loads((ISSUES / "weekday" / "content.json").read_text()))
    req = ChartRequest(source="yahoo", id="^TNX", title="10-year yield")
    c.big_read.chart = req
    for s in c.top_3:
        s.chart = req
    got = charts.requests_in(c)
    assert [w for w, _ in got] == ["big_read", "top_3[0]", "top_3[1]"] and len(got) == charts.MAX_CHARTS


def test_chart_title_cannot_carry_a_number():
    with pytest.raises(ValidationError):
        ChartRequest(source="bls", id="CUUR0000SA0", title="Inflation hits 3.7%")


def test_formatting_and_alt_text():
    f = charts.fmt_value
    assert f(72, "%") == "72%" and f(3.7, "%") == "3.7%" and f(4.25, "") == "4.25" and f(-33, "") == "−33"
    assert f(6812.4, "") == "6,812" and f(165.0, "") == "165"
    bars = {"kind": "bars", "unit": "%", "bars": [("Hold", 72), ("Cut 25bps", 26)]}
    assert charts.alt_text("Fed odds", "Kalshi", bars) == "Chart: Fed odds. Hold 72%; Cut 25bps 26%. Source: Kalshi."
    assert charts.numbers(bars) == [72, 26]


def test_failed_fetch_becomes_ok_false(tmp_path):
    def boom(req, now):
        raise RuntimeError("Kalshi 503")
    ch = charts.make(ChartRequest(source="kalshi", id="X", title="t"), "chart1", tmp_path, NOW, fetch=boom)
    assert ch["ok"] is False and "503" in ch["error"]


def test_kalshi_odds_from_event(monkeypatch, tmp_path):
    event = {"event": {"series_ticker": "KXFEDDECISION"}, "markets": [
        {"ticker": "A", "yes_sub_title": "Hold", "last_price_dollars": "0.7200"},
        {"ticker": "B", "yes_sub_title": "Cut 25bps", "last_price_dollars": None,
         "yes_bid_dollars": "0.2500", "yes_ask_dollars": "0.2700"}]}
    monkeypatch.setattr(charts, "get_json", lambda url, params=None, headers=None: event)
    req = ChartRequest(source="kalshi", id="KXFEDDECISION-26DEC", title="Fed odds", view="odds")
    s = charts.fetch_kalshi(req, NOW)
    assert s["bars"] == [("Hold", 72), ("Cut 25bps", 26)]
    ch = charts.make(req, "chart1", tmp_path, NOW)
    assert ch["ok"] and (tmp_path / "chart1.png").stat().st_size > 1000 and ch["width"] == 504


def test_bls_year_over_year(monkeypatch):
    rows = [{"year": str(y), "period": f"M{m:02d}", "value": str(100 + (y - 2025) * 12 + m)}
            for y in (2025, 2026) for m in range(1, 13) if (y, m) <= (2026, 10)]

    class R:
        def raise_for_status(self): pass
        def json(self): return {"status": "REQUEST_SUCCEEDED", "Results": {"series": [{"data": rows}]}}
    monkeypatch.setattr(charts.requests, "post", lambda *a, **k: R())
    s = charts.fetch_bls(ChartRequest(source="bls", id="CUUR0000SA0", title="CPI", transform="yoy", period="1y"), NOW)
    assert s["x"][-1] == date(2026, 10, 1) and s["unit"] == "%"
    assert s["lines"][0]["values"][-1] == round((122 / 110 - 1) * 100, 1)
