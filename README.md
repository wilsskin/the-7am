# The 7AM
A personal morning newsletter, emailed every morning before 7am.

[wilsonskinner.com](https://wilsonskinner.com)

---

## What It Does
- Starts the day with weather, subway alerts, calendar events and birthdays
- Covers markets, my holdings and earnings with exact numbers, no ads
- Summarizes the news that matters, with links to the original reporting

## How It's Built
Python collectors pull market, earnings, weather, transit, sports and meme data from free sources. A Claude scheduled task reads my Google Calendar, picks and summarizes the news, and the script renders it into an HTML email that shares the design system of my portfolio. Sent with Resend.

**Stack:** Python, Jinja, Claude scheduled tasks, Resend
