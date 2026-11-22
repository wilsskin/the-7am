from brief import feedback

REPLY = """Love the big read today. Can the sports card show the Giants too?

On Tue, Nov 24, 2026 at 7:00 AM The 7AM <onboarding@resend.dev> wrote:
> The Nasdaq fell 10% last week...
> more quoted text"""

WRAPPED = """Shorter intro please.

On Wed, Nov 25, 2026 at 7:00 AM The 7AM <onboarding@resend.dev>
wrote:
> quoted"""


def test_strip_quoted():
    assert feedback.strip_quoted(REPLY) == "Love the big read today. Can the sports card show the Giants too?"
    assert feedback.strip_quoted(WRAPPED) == "Shorter intro please."
    assert feedback.strip_quoted("> only quote") == ""


def test_add_newest_first_and_no_duplicates(tmp_path):
    f = tmp_path / "FEEDBACK.md"
    f.write_text(feedback.HEADER)
    m1 = {"id": "a1", "date": "2026-11-24", "subject": "Re: The Nasdaq fell", "body": REPLY}
    assert feedback.add([m1], f) == 1
    m2 = {"id": "b2", "date": "2026-11-25", "subject": "Re: Second issue", "body": WRAPPED}
    assert feedback.add([m1, m2], f) == 1          # a1 already filed
    text = f.read_text()
    assert text.startswith("# Feedback")
    assert text.index("gmail:b2") < text.index("gmail:a1")
    assert "- [ ] **2026-11-25** · Re: Second issue <!-- gmail:b2 -->\n  Shorter intro please." in text
    assert ">" not in text.split("-->")[1].split("\n- ")[0]
    assert feedback.add([m1, m2], f) == 0
