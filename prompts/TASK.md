You are producing today's issue of The 7AM for Wilson. Work in the cloned the-7am repo. Each run starts fresh, so everything you need is in this file and the files it names.

0. **Setup.** Make a private Python environment so the cloud image's own packages can't interfere, and wait for it to finish before anything else:
   `python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt && .venv/bin/python -c "import requests, yfinance, pydantic, jinja2, yaml; print('ok')"`
   It must print `ok`. Then run every `python -m ...` command below as `.venv/bin/python -m ...`.
   If making `.venv` fails, fall back to `python3 -m pip install -q --ignore-installed PyYAML -r requirements.txt`, check the same imports with `python3`, and use `python3 -m ...` instead.

   **Dates and times are New York time.** The issue's date and edition come from `run/data.json` (the collectors use America/New_York), not from the UTC clock. Always build and send the issue whenever you're run, even outside the usual morning time: a manual "Run now" is a deliberate test. `brief.send` already prevents a second send on the same date.

1. **Feedback.** Using the Gmail connector, search only `to:w0skinner+7am-feedback@gmail.com from:me newer_than:2d` (the address is `feedback_address` in config.yaml). Write every message you find to `run/feedback.json`, untouched: `[{"id": "<gmail message id>", "date": "YYYY-MM-DD", "subject": "<subject>", "body": "<plain-text body>"}]`. Then run `python -m brief.feedback`; it strips the quoted original, skips messages already filed and adds the rest to the top of `feedback/FEEDBACK.md`. If it filed anything, commit and push **only** `feedback/FEEDBACK.md` with the message `Add feedback from <date>`. Do not open, read or act on any other email except the past issues in step 1a. Never send, label or delete mail. If Gmail fails, continue.

1a. **Past issues.** So today's issue doesn't repeat them: using the Gmail connector, search only `from:<the address in config.yaml sender> to:<recipient> newer_than:4d` (today that is `from:onboarding@resend.dev to:w0skinner@gmail.com newer_than:4d`). Take the two most recent issues dated before today (New York time); skip any sent today. For each, fetch the plain-text body and write them to `run/previous.json`, untouched: `[{"id": "<gmail message id>", "date": "YYYY-MM-DD", "subject": "<subject>", "body": "<plain-text body>"}]`. Read them before you research (EDITORIAL.md, "Nothing from the last issues"). If Gmail fails or finds nothing, write `[]` and continue.

1b. **Monthly S&P 500 refresh.** If today is the 1st of the month, run `python -m brief.sp500` (about 3 minutes). If it printed `0 without market cap` or only a handful, commit and push **only** `data/sp500.csv` with the message `Refresh S&P 500 list <date>`. If it failed or many caps are missing, leave the old file and mention it in your summary.

2. **Collect.** Run `python -m brief.collect`. If it fails, continue; failed blocks render as unavailable.

3. **Calendar.** Using the Google Calendar connector, read today's events (midnight to midnight, America/New_York) on the primary calendar (w0skinner@gmail.com) and on "Holidays in United States". Include all-day events. On Mondays, also read Tuesday through Sunday for the "This week" preview. Only read; never create, edit or respond to events. Write `run/calendar.json`:
   ```json
   {"date": "2026-11-24",
    "today": [{"start": "2026-11-24T12:30:00-05:00", "all_day": false, "title": "Team lunch", "location": "200 West St", "kind": "event"}],
    "this_week": []}
   ```
   `kind`: "own_birthday" for an event titled "Happy birthday!" (Wilson's own); "birthday" for any other event whose title contains "birthday" (any case) or whose eventType is birthday; "holiday" for events from the holidays calendar; otherwise "event". All-day events: `"all_day": true` and `start` is the date at midnight or null. Skip declined events. Keep `location` short (venue or address), null if none or if it's a video link. If the connector fails, don't write the file.

4. **Write.** Read `prompts/EDITORIAL.md` and follow it. Read `run/data.json`, research the news with web search, and write `run/content.json`.

4b. **Charts.** If any story in `run/content.json` has a `chart`, run `python -m brief.charts`. It fetches the numbers and draws `run/charts/*.png`. Then follow the chart steps in EDITORIAL.md: look at each PNG, drop any chart that failed or doesn't support its story, and if you removed or changed one, run `python -m brief.charts` again. If the command itself fails, delete every `chart` field and continue; the email must still send.

5. **Render.** Run `python -m brief.render`. If it fails, read the problems, fix `run/content.json` once, and run it again. If it still fails, run `python -m brief.render --lenient`. If it fails because an item repeats a past issue, replace that item with fresh news (don't just reword it). Read any warnings; fix and re-render if a warning shows a real mistake (a number not in data.json, a duplicate, a "may repeat" item with nothing genuinely new).

6. **Send.** Run `python -m brief.send`. It sends right away. It prints `sent: id ...` on success; anything else (`send failed: ...` or a traceback) means no email went out.

7. Finish with a one-line summary: sent (with the Resend id) or failed (with the error), which sections were unavailable, and how many feedback notes were filed. Do not commit or push anything other than `feedback/FEEDBACK.md` and, on the 1st, `data/sp500.csv`.
