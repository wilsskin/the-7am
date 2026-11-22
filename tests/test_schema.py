"""Schema checks and the 'email always sends' rule for collectors."""
import pytest
from pydantic import ValidationError

from brief import schema
from brief.collect import __main__ as collect_main
from brief.common import ET, load_config


def test_every_collector_failing_still_gives_valid_data(monkeypatch):
    def boom(cfg, now):
        raise RuntimeError("offline")
    monkeypatch.setattr(collect_main, "COLLECTORS", {k: boom for k in collect_main.COLLECTORS})
    from datetime import datetime
    data = collect_main.collect(datetime(2026, 11, 24, 6, 22, tzinfo=ET), load_config())
    d = schema.Data.model_validate(data)
    assert d.edition == "weekday" and not d.markets.ok and d.markets.error == "RuntimeError: offline"


def story(h="Headline with a verb"):
    return {"headline": h, "body": "One.\n\nTwo.", "link": {"title": "t", "url": "https://www.wsj.com/a", "source": "WSJ"}}


def content(**over):
    c = {"date": "2026-11-24", "edition": "weekday", "subject": "Nvidia beat, and it still wasn't enough.",
         "intro": "One. Two. Three.", "section_desc": {"your_day": "x"}, "big_read": story(),
         "top_3": [story(), story(), story()],
         "latest": {"sports": [], "business": [story()["link"]]}}
    c.update(over)
    return c


def test_content_valid_and_latest_reordered():
    c = schema.Content.model_validate(content())
    assert list(c.latest) == ["business", "sports"]


def test_top3_must_be_three():
    with pytest.raises(ValidationError):
        schema.Content.model_validate(content(top_3=[story()]))


def test_subject_max_length():
    with pytest.raises(ValidationError):
        schema.Content.model_validate(content(subject="x" * 71))


def test_holding_headline_starts_with_ticker():
    ok = {**story("PLTR: Army expands its software contract"), "ticker": "PLTR"}
    schema.Content.model_validate(content(holdings_news=[ok]))
    bad = {**story("Army expands Palantir contract"), "ticker": "PLTR"}
    with pytest.raises(ValidationError):
        schema.Content.model_validate(content(holdings_news=[bad]))


def test_calendar():
    cal = schema.Calendar.model_validate({"date": "2026-11-24", "today": [
        {"start": "2026-11-24T12:30:00-05:00", "title": "Team lunch", "location": "200 West St"},
        {"all_day": True, "title": "Lily Bien's birthday", "kind": "birthday"}]})
    assert cal.today[1].kind == "birthday" and cal.this_week == []
