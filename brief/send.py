"""python -m brief.send [--dry-run] [--test]

Sends run/issue.html (+ issue.txt) through Resend: one requests.post, no SDK.

- Icons in run/render.json are attached inline (content_id), matching src="cid:<name>".
- reply_to is config.feedback_address, so hitting Reply files feedback (BUILD_PLAN §10b).
- It sends the moment the run finishes. No scheduled_at: Resend can't schedule emails
  with attachments (our inline icons), which is why the 7:00 hold silently failed (Nov 23).
- If render failed completely, it sends a plain-text email with what exists plus the error.
  The email always sends.
- One issue per day: the Idempotency-Key is the date, so a retried run can't double-send.
  --test uses a unique key, for trying things out.

Needs RESEND_API_KEY. --dry-run writes run/payload.json instead of sending.
"""
import argparse
import base64
import json
import os
import sys
from datetime import datetime

import requests

from brief.common import ET, ROOT, RUN_DIR, TIMEOUT, load_config, now_et

API = "https://api.resend.com/emails"
ICONS = ROOT / "templates" / "icons"


def attachments(icons: list[str]) -> list[dict]:
    return [{"filename": f"{n}.png", "content": base64.b64encode((ICONS / f"{n}.png").read_bytes()).decode(),
             "content_type": "image/png", "content_id": n} for n in icons]


def fallback_text(run_dir, error: str) -> tuple[str, str]:
    """Plain-text email for when render failed: what we have, plus the error."""
    lines = ["The 7AM could not be rendered this morning.", "", f"Error: {error}", ""]
    txt = run_dir / "issue.txt"
    if txt.exists():
        lines += [txt.read_text()]
    else:
        try:
            d = json.loads((run_dir / "data.json").read_text())
            if d["markets"]["ok"]:
                lines.append("Markets at the last close:")
                for q in d["markets"]["indices"] + d["markets"]["crypto"]:
                    p = q["change_1d_pct"]
                    lines.append(f"  {q['label']}: {q['price']:,} ({'' if p is None else f'{p:+.2f}%'})")
            if d["weather"]["ok"]:
                lines += ["", f"Weather: {d['weather']['summary']} {d['weather']['precip'] or ''}".strip()]
        except Exception as e:  # nothing usable on disk
            lines.append(f"(data.json unavailable too: {e})")
    return "\n".join(lines).strip() + "\n", None


def build_payload(cfg: dict, run_dir, now: datetime) -> dict:
    meta_path, html_path = run_dir / "render.json", run_dir / "issue.html"
    base = {"from": cfg["sender"], "to": [cfg["recipient"]], "reply_to": cfg["feedback_address"]}
    if meta_path.exists() and html_path.exists():
        meta = json.loads(meta_path.read_text())
        payload = {**base, "subject": meta["subject"], "html": html_path.read_text(),
                   "text": (run_dir / "issue.txt").read_text()}
        if meta["icons"]:
            payload["attachments"] = attachments(meta["icons"])
    else:
        err_path = run_dir / "render_error.txt"
        error = err_path.read_text().strip() if err_path.exists() else "render produced no output"
        text, _ = fallback_text(run_dir, error)
        payload = {**base, "subject": f"{cfg['brand']['name']}, {now:%a %b} {now.day} (plain-text fallback)", "text": text}
    return payload


def post(payload: dict, idempotency_key: str) -> dict:
    key = os.environ.get("RESEND_API_KEY")
    if not key:
        raise RuntimeError("RESEND_API_KEY is not set")
    r = requests.post(API, json=payload, timeout=TIMEOUT,
                      headers={"Authorization": f"Bearer {key}", "Idempotency-Key": idempotency_key})
    if r.status_code >= 300:
        raise RuntimeError(f"Resend {r.status_code}: {r.text[:500]}")
    return r.json()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="write run/payload.json, don't send")
    p.add_argument("--test", action="store_true", help="send with a one-off key (for testing)")
    p.add_argument("--run-dir", default=str(RUN_DIR))
    a = p.parse_args()
    from pathlib import Path
    run_dir, cfg, now = Path(a.run_dir), load_config(), now_et()
    payload = build_payload(cfg, run_dir, now)
    key = f"the-7am-{now:%Y-%m-%d}" + (f"-test-{now:%H%M%S}" if a.test else "")
    if a.dry_run:
        shown = {**payload, "html": f"<{len(payload.get('html', ''))} chars>",
                 "attachments": [{**x, "content": f"<{len(x['content'])} b64 chars>"} for x in payload.get("attachments", [])]}
        (run_dir / "payload.json").write_text(json.dumps(shown, indent=2, ensure_ascii=False))
        print(f"dry run: wrote {run_dir / 'payload.json'} (idempotency key {key})")
        return
    try:
        res = post(payload, key)
    except Exception as e:
        print(f"send failed: {e}", file=sys.stderr)
        sys.exit(1)
    (run_dir / "send.json").write_text(json.dumps({"id": res.get("id"), "sent_at": now.isoformat(), "key": key}, indent=2))
    print(f"sent: id {res.get('id')}, subject: {payload['subject']}")


if __name__ == "__main__":
    main()
