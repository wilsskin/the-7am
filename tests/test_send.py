"""send.py: payload shape, scheduling, inline icons, fallback. Resend is faked; nothing is sent."""
import base64
import json
import shutil
from datetime import datetime
from pathlib import Path

import pytest

from brief import render, send
from brief.common import ET, load_config

ISSUES = Path(__file__).parent / "fixtures" / "issues"
CFG = load_config()


@pytest.fixture
def rendered(tmp_path):
    d = tmp_path / "run"
    shutil.copytree(ISSUES / "weekday", d)
    render.render(d, now=datetime(2026, 11, 24, 6, 41, tzinfo=ET))
    return d


def test_payload_scheduled_for_7am_with_inline_icons(rendered):
    p = send.build_payload(CFG, rendered, datetime(2026, 11, 24, 6, 45, tzinfo=ET))
    assert p["from"] == "The 7AM <onboarding@resend.dev>" and p["to"] == ["w0skinner@gmail.com"]
    assert p["reply_to"] == "w0skinner+7am-feedback@gmail.com"
    assert p["subject"] == "Nvidia beat, and it still wasn't enough."
    assert p["scheduled_at"] == "2026-11-24T07:00:00-05:00"
    ids = sorted(a["content_id"] for a in p["attachments"])
    assert ids == ["calendar", "cloud", "subway"]
    for a in p["attachments"]:
        assert f'src="cid:{a["content_id"]}"' in p["html"]
        assert base64.b64decode(a["content"])[:8] == b"\x89PNG\r\n\x1a\n"
    assert p["text"].startswith("The 7AM")


def test_after_7_sends_immediately(rendered):
    p = send.build_payload(CFG, rendered, datetime(2026, 11, 24, 7, 5, tzinfo=ET))
    assert "scheduled_at" not in p


def test_test_mode_sends_immediately(rendered):
    p = send.build_payload(CFG, rendered, datetime(2026, 11, 24, 6, 45, tzinfo=ET), immediate=True)
    assert "scheduled_at" not in p


def test_fallback_when_render_failed(tmp_path):
    d = tmp_path / "run"
    shutil.copytree(ISSUES / "weekday", d)
    (d / "render_error.txt").write_text("RenderError: issue.html is too big\n")
    p = send.build_payload(CFG, d, datetime(2026, 11, 24, 6, 45, tzinfo=ET))
    assert "html" not in p and "plain-text fallback" in p["subject"]
    assert "issue.html is too big" in p["text"] and "S&P 500: 6,812.4 (-0.62%)" in p["text"]


def test_fallback_with_nothing_on_disk(tmp_path):
    p = send.build_payload(CFG, tmp_path, datetime(2026, 11, 24, 6, 45, tzinfo=ET))
    assert "render produced no output" in p["text"] and "data.json unavailable" in p["text"]


def test_failed_render_leaves_no_stale_issue(tmp_path):
    d = tmp_path / "run"
    shutil.copytree(ISSUES / "weekday", d)
    render.render(d, now=datetime(2026, 11, 24, 6, 41, tzinfo=ET))
    assert (d / "issue.html").exists()
    c = json.loads((d / "content.json").read_text())
    c["memes"][0] = "https://i.redd.it/not-a-candidate.jpg"
    (d / "content.json").write_text(json.dumps(c))
    with pytest.raises(render.RenderError):
        render.render(d, now=datetime(2026, 11, 24, 6, 41, tzinfo=ET))
    assert not (d / "issue.html").exists() and not (d / "render.json").exists()


def test_post_uses_bearer_key_and_idempotency(monkeypatch):
    seen = {}

    class R:
        status_code = 200
        def json(self):
            return {"id": "abc"}

    def fake_post(url, json, timeout, headers):
        seen.update(url=url, headers=headers, json=json)
        return R()
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setattr(send.requests, "post", fake_post)
    assert send.post({"subject": "x"}, "the-7am-2026-11-24") == {"id": "abc"}
    assert seen["url"] == "https://api.resend.com/emails"
    assert seen["headers"] == {"Authorization": "Bearer re_test", "Idempotency-Key": "the-7am-2026-11-24"}


def test_post_without_key_fails(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="RESEND_API_KEY"):
        send.post({}, "k")
