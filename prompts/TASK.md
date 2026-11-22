You are producing today's issue of The 7AM for Wilson. Work in the cloned the-7am repo. Each run starts fresh, so everything you need is in this file and the files it names.

0. **Setup.** `pip install -q -r requirements.txt`.

1. **Feedback.** Using the Gmail connector, search only `to:w0skinner+7am-feedback@gmail.com from:me newer_than:2d` (the address is `feedback_address` in config.yaml). Write every message you find to `run/feedback.json`, untouched: `[{"id": "<gmail message id>", "date": "YYYY-MM-DD", "subject": "<subject>", "body": "<plain-text body>"}]`. Then run `python -m brief.feedback`; it strips the quoted original, skips messages already filed and adds the rest to the top of `feedback/FEEDBACK.md`. If it filed anything, commit and push **only** `feedback/FEEDBACK.md` with the message `Add feedback from <date>`. Do not open, read or act on any other email. Never send, label or delete mail. If Gmail fails, continue.

2. **Collect.** Run `python -m brief.collect`. If it fails, continue; failed blocks render as unavailable.

3. **Calendar.** Using the Google Calendar connector, read today's events (midnight to midnight, America/New_York) on the primary calendar (w0skinner@gmail.com) and on "Holidays in United States". Include all-day events. On Mondays, also read Tuesday through Sunday for the "This week" preview. Only read; never create, edit or respond to events. Write `run/calendar.json`:
   ```json
   {"date": "2026-11-24",
    "today": [{"start": "2026-11-24T12:30:00-05:00", "all_day": false, "title": "Team lunch", "location": "200 West St", "kind": "event"}],
    "this_week": []}
   ```
   `kind`: "own_birthday" for an event titled "Happy birthday!" (Wilson's own); "birthday" for any other event whose title contains "birthday" (any case) or whose eventType is birthday; "holiday" for events from the holidays calendar; otherwise "event". All-day events: `"all_day": true` and `start` is the date at midnight or null. Skip declined events. Keep `location` short (venue or address), null if none or if it's a video link. If the connector fails, don't write the file.

4. **Write.** Read `prompts/EDITORIAL.md` and follow it. Read `run/data.json`, research the news with web search, and write `run/content.json`.

5. **Render.** Run `python -m brief.render`. If it fails, read the problems, fix `run/content.json` once, and run it again. If it still fails, run `python -m brief.render --lenient`. Read any warnings; fix and re-render if a warning shows a real mistake (a number not in data.json, a duplicate).

6. **Send.** Run `python -m brief.send`.

7. Finish with a one-line summary: sent or failed, which sections were unavailable, and how many feedback notes were filed. Do not commit or push anything other than `feedback/FEEDBACK.md`.
