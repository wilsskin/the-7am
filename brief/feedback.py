"""python -m brief.feedback

Files Wilson's replies into feedback/FEEDBACK.md (BUILD_PLAN.md §10b). Claude reads the
messages through the Gmail connector and writes them, untouched, to run/feedback.json:
  [{"id": "<gmail message id>", "date": "2026-11-24", "subject": "Re: ...", "body": "..."}]
This script strips the quoted original, skips ids already filed, and adds new entries at
the top of the list, newest first. Prints how many it added.
"""
import json
import re

from brief.common import ROOT, RUN_DIR

FILE = ROOT / "feedback" / "FEEDBACK.md"
HEADER = "# Feedback\n\nWilson's replies to the issue, newest first. Filed by the scheduled task (BUILD_PLAN.md §10b).\n"
QUOTE_START = re.compile(r"^\s*On .+wrote:\s*$")


def strip_quoted(body: str) -> str:
    """Drop everything from the "On ... wrote:" line down, and any line starting with ">"."""
    lines = body.replace("\r\n", "\n").split("\n")
    out = []
    for i, line in enumerate(lines):
        # Gmail sometimes wraps "On <date>, <name> <addr>" onto two lines before "wrote:".
        joined = line + " " + lines[i + 1] if i + 1 < len(lines) else line
        if QUOTE_START.match(line) or (line.strip().startswith("On ") and QUOTE_START.match(joined)):
            break
        if line.lstrip().startswith(">"):
            continue
        out.append(line)
    return "\n".join(out).strip()


def entry(m: dict) -> str:
    text = strip_quoted(m["body"]) or "(empty reply)"
    body = "\n".join("  " + l if l.strip() else "" for l in text.split("\n"))
    return f"- [ ] **{m['date']}** · {m['subject'].strip()} <!-- gmail:{m['id']} -->\n{body}\n"


def add(messages: list[dict], path=FILE) -> int:
    current = path.read_text() if path.exists() else HEADER
    filed = set(re.findall(r"<!-- gmail:([^ ]+) -->", current))
    new = [m for m in sorted(messages, key=lambda m: m["date"], reverse=True) if m["id"] not in filed]
    if not new:
        return 0
    head, _, rest = current.partition("\n- ")
    rest = ("- " + rest) if rest else ""
    path.write_text(head.rstrip() + "\n\n" + "\n".join(entry(m) for m in new) + ("\n" + rest if rest else ""))
    return len(new)


def main():
    src = RUN_DIR / "feedback.json"
    if not src.exists():
        print("no run/feedback.json; nothing to file")
        return
    n = add(json.loads(src.read_text()))
    print(f"filed {n} new feedback note{'s' if n != 1 else ''}")


if __name__ == "__main__":
    main()
