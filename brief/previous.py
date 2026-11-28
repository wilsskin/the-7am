"""The last issues Wilson received, so today's doesn't repeat them (Wilson, Nov 27, 2026).

Each run starts from a fresh clone with no memory, so the morning task copies the plain-text
version of the last two issues from Gmail into run/previous.json, untouched:

    [{"id": "<gmail message id>", "date": "YYYY-MM-DD", "subject": "...", "body": "<plain text>"}]

The plain-text part (email.txt.j2) lists every story and its link in a simple, stable
format; issues before Nov 28, 2026 also had their HTML links rewritten by Resend's click
tracking. This module turns those bodies into the links and headlines render.py checks
today's content against. Missing or empty file: nothing to check, the issue still renders.
"""
import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

URL = re.compile(r"https?://[^\s)>\]]+")
# What the plain-text template puts around a headline: "- " bullets, "(Source) url" / "Source: url" tails.
TAIL = re.compile(r"\s*(\([^()]{1,40}\))?:?\s*https?://\S+\s*$")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“$])")


@dataclass
class Previous:
    issues: list[dict] = field(default_factory=list)     # [{date, subject}]
    urls: set[str] = field(default_factory=set)          # normalized: host + path
    heads: list[str] = field(default_factory=list)       # headline-like lines: first sentence of every line
    sentences: list[str] = field(default_factory=list)   # every sentence

    def label(self) -> str:
        return " and ".join(f"{i['date']} ({i['subject']})" for i in self.issues) or "previous issues"


def norm_url(url: str) -> str:
    u = re.sub(r"^https?://(www\.)?", "", str(url).strip()).split("?")[0].split("#")[0]
    return u.rstrip("/.,;")


def clean(line: str) -> str:
    line = TAIL.sub("", line.strip())
    line = re.sub(r"^[-•]\s+", "", line)
    return re.sub(r"^[^\w\"“$]+", "", line).strip()      # leading emoji or symbols


def parse(issues: list[dict], brand: str = "The 7AM", before: date | None = None) -> Previous:
    """Only real issues (the body starts with the brand), only from before `before` (today)."""
    prev = Previous()
    keep = [i for i in issues if (i.get("body") or "").lstrip().startswith(brand)
            and (before is None or str(i.get("date", "")) < before.isoformat())]
    for issue in sorted(keep, key=lambda i: str(i.get("date", "")), reverse=True)[:2]:
        prev.issues.append({"date": issue.get("date"), "subject": issue.get("subject")})
        body = issue["body"]
        prev.urls |= {norm_url(u) for u in URL.findall(body)}
        for raw in body.splitlines():
            line = clean(raw)
            if len(line.split()) < 4:
                continue
            parts = [p for p in SENTENCE_END.split(line) if p]
            prev.heads.append(parts[0])
            prev.sentences += [p for p in parts if len(p.split()) >= 4]
    return prev


def load(run_dir: Path, brand: str = "The 7AM", before: date | None = None) -> Previous:
    try:
        raw = json.loads((run_dir / "previous.json").read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return Previous()
    return parse(raw if isinstance(raw, list) else [], brand, before)
