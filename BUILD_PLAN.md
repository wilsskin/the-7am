# The 7AM: Build Plan

How the pipeline works and why, plus every product decision made so far. Read `CLAUDE.md` first. Visual rules are in `DESIGN_SYSTEM.md`; ask Wilson before changing anything visual.

The 7AM is a personal, ad-free morning newsletter emailed to Wilson every morning (around 6:35am ET), modeled on Exec Sum and Morning Brew, built around his holdings, his calendar and his interests. It is a sibling of Wilson's portfolio ([wilsskin/wms-portfolio](https://github.com/wilsskin/wms-portfolio)): same design tokens, same plain-spoken voice, same "simple over clever" engineering.

## 0. Ground rules

- **No cost beyond Wilson's Claude plan.** No Anthropic API key, no paid APIs, no paid hosting. Every service is on a free tier. If something seems to need money, stop and ask.
- **Show, don't describe.** Changes end with something Wilson can look at: a JSON file, a screenshot, an email in his inbox.
- Everything else about working with Wilson is in `CLAUDE.md`.

---

## 1. Architecture

One GitHub repo (wilsskin/the-7am, cloned locally at `~/code/the-7am`), run daily by a **Claude cloud scheduled task**. Code owns the parts that must be exact. Claude owns the parts that need judgment.

| Layer | Owner | Why |
|---|---|---|
| Market prices, earnings numbers, weather, subway alerts, scores, meme candidates | Python collectors (deterministic) | Numbers must never come from an LLM reading articles |
| Calendar events + birthdays | Claude, via the Google Calendar connector | Connector already authorized, no OAuth setup |
| Feedback and past issues | Claude, via the Gmail connector, read only | §10b; past issues stop repeats (§6) |
| Story selection, summaries, headlines, links | Claude, using web search | Needs editorial judgment |
| Layout | Jinja2 templates in the repo | Identical layout every day; Claude never writes HTML |
| Sending | Resend API | Reliable delivery to Gmail, free tier |

### Daily run

1. The task fires at **6:28am ET**. Its cron is UTC with no time zone: `28 11 * * *` while New York is on EST, `28 10 * * *` on EDT. It must be changed by hand at each clock change; the footer reminds Wilson beforehand (`reminders` in config.yaml). Off the hour on purpose: on-the-hour runs can start late.
2. Claude clones the repo and follows `prompts/TASK.md`: files feedback (§10b), saves the last two issues for the no-repeat check, runs `python -m brief.collect` → `run/data.json`.
3. Claude reads today's calendar → `run/calendar.json`.
4. Claude follows `prompts/EDITORIAL.md`, researches the news, writes `run/content.json` (`brief/schema.py`). Optional charts: `python -m brief.charts`.
5. `python -m brief.render` validates everything, enforces the rules (allowlist, dedupe, no repeats, word caps) and writes `run/issue.html` + `run/issue.txt`.
6. `python -m brief.send` sends via Resend immediately (lands around 6:35am ET). Never use `scheduled_at`: Resend can't schedule emails with attachments, and every issue has inline icons (this silently dropped the Nov 23 issue).

### Failure rules (non-negotiable)

- If a collector fails, its section renders "… unavailable this morning." Never fill numbers from search.
- If content.json fails validation, Claude gets one retry. If it still fails, `--lenient` renders whatever is valid, dropping only the bad items.
- If render fails completely, send a plain-text email with whatever exists plus the error.
- The email always sends. A missing section is fine. A missing email is not.

---

## 2. Repo layout

```
the-7am/
  CLAUDE.md  README.md  BUILD_PLAN.md  DESIGN_SYSTEM.md  SETUP.md
  config.yaml               # all personal settings (§3)
  prompts/
    TASK.md                 # the scheduled task's steps (§8)
    EDITORIAL.md            # section rules, sources, style (§6)
  brief/
    collect/                # markets, earnings, market_calendar, weather, mta, sports, memes
    common.py  fmt.py  tokens.py  schema.py
    render.py  send.py  charts.py  feedback.py  previous.py  sp500.py
    run.py                  # local only: --fixture, --dry-run; never sends
  templates/
    email.html.j2  email.txt.j2
    icons/                  # 60px PNG line icons (make_icons.swift)
  brand/7am-twotone.png     # logo, for the sender avatar (§12)
  data/sp500.csv            # tickers, names, market caps; refreshed monthly
  feedback/FEEDBACK.md      # Wilson's replies, newest first (§10b)
  tests/                    # pytest; fixtures/issues/ are the sample issues
  run/                      # gitignored, per-run output
```

Python 3.12. Dependencies are in `requirements.txt` (runtime) and `requirements-dev.txt` (pytest, Playwright). No CSS inliner (the Jinja macros write inline styles from `tokens.py`), no Resend SDK (one `requests.post`). Ask Wilson before adding anything.

Keep the repo outside iCloud Drive: iCloud syncing a `.git` folder causes corruption. The iCloud `projects/newsletter` folder holds a reference copy of the docs only.

---

## 3. config.yaml

All personal settings live in `config.yaml`: recipient, sender, feedback address, location, subway lines and stops, indices, crypto, holdings (in card order), the earnings universe, teams, meme sources, allowed news domains and leisure domains, and footer reminders. The file is the source of truth; its comments say what each setting does.

---

## 4. Data sources (collectors)

| Data | Source | Notes |
|---|---|---|
| Index, ETF, crypto, holdings prices | `yfinance` | Price at the last 4pm ET close, 1-day % (vs the close before it), week-to-date % (vs the prior week's last close). Monday: YTD % instead of WTD. **Crypto uses the same 4pm ET moments as stocks, not a rolling 24h window**: the open of the 16:00 ET hourly bar (fallback: close of the 15:00 bar). Weekend: crypto as of 4pm ET Friday. |
| Big movers | `yfinance` over `data/sp500.csv` | The 8 biggest absolute 1-day % moves among $100B+ companies. Claude picks 2–3 and writes why. |
| Earnings results + calendar | Finnhub `/calendar/earnings` (free key) | Universe: the 200 biggest S&P 500 companies plus holdings. Surprise % = (actual − estimate) / \|estimate\|, to 0.1%. After-hours move: latest extended-hours price (`yfinance` prepost) vs that day's close (1pm on early-close days). Next trading day's reporters → "Deere reports tomorrow." appended to the Earnings description. |
| Market closures / early closes | `exchange_calendars` (XNYS) | Any closure or early close today or later this week → a fixed sentence ("Markets close Thursday for Thanksgiving, early close Friday at 1pm.") appended to the Before the bell description. |
| Weather | Open-Meteo (no key); backup: National Weather Service `api.weather.gov` (no key) | High/low °F, conditions, the day's outlook, precipitation timing. Open-Meteo returned 429 from the shared cloud IP on Nov 27, 2026, hence the backup. |
| Subway alerts | MTA GTFS-RT alerts JSON (`api-endpoint.mta.info`, no key) | 4/5 alerts that touch the Fulton St–14 St-Union Sq ride (`subway_stops`); line-wide delays stay. Max 2. |
| Last night's scores | ESPN public scoreboard JSON | Followed teams, games finished since the previous run. One request per date; ESPN rejects date ranges. |
| This week's games (Mondays) | ESPN team schedule JSON | Teams with `week_preview: true`, Monday through Sunday. |
| Memes | Short Squeez "Memes of the Day", Exec Sum "Meme Cleanser", Lemmy (no keys); Reddit only if its API is ever approved | Newsletter issues under 26 hours old, so nothing repeats; Lemmy fills. Claude picks up to 6. Parsed with regex: a newsletter redesign makes that source return nothing. |
| Supporting charts (on request) | Kalshi, Polymarket, BLS, Yahoo (all free, no keys) | Not a daily collector. Claude adds a `chart` request to a story; `python -m brief.charts` fetches the numbers and draws a PNG, so chart numbers never come from Claude. FRED timed out, so it isn't used. BLS never published October 2025 CPI. |

Every `data.json` block has `ok`, `as_of` and, if it failed, `error`.

---

## 5. Sections (in order)

Editions: **Mon** shows YTD instead of WTD, a "This week" calendar preview, "Reporting this week" earnings and this week's games. **Tue–Fri** is standard. **Sat/Sun**: Before the bell becomes "Markets" with Bitcoin and Ether only; no Holdings, Earnings or On deck today. **Holiday / early close**: a weekday issue whose Before the bell description ends with the closure sentence. Every section has a label plus a one-line description Claude writes that morning (`section_desc`).

| # | Section | Source | Spec |
|---|---|---|---|
| 1 | Subject + intro | Claude | Subject: punchy hook, under 60 characters. Intro: 2–5 sentences; the first is the one thing to know and the inbox preview. |
| 2 | Your day | data + calendar + Claude | Weather, 4/5 alerts, today's events, birthdays ("Lily Bien's birthday 🎂"), Wilson's own birthday as a theme pill, US holidays. Monday: "This week". Then "NYC today": up to 3 links. An empty calendar is left out, never mentioned. |
| 3 | Before the bell | data + Claude | Market card (S&P 500, Nasdaq, Dow, Bitcoin, Ether). Big movers: "NVDA −6.40%", then 1–2 sentences on why. "On deck today": scheduled events in time order, untimed items last with "–". |
| 3b | Earnings | data | Yesterday's big reporters: revenue and EPS as the actual plus surprise ("57.0B (+3.3%)"), and the after-hours move. Monday: "Reporting this week", company names per day. Skipped if empty. |
| 4 | Your holdings | data + Claude | One row per holding. A story for **every** holding with relevant news, no cap; headline starts with the ticker. |
| 5 | The big read | Claude | The most important story, ~300 words in 6–8 short paragraphs, headline as the first sentence. |
| 6 | Top 3 | Claude | 3 more big stories, ~100 words each, with an emoji. |
| 7 | The latest | Claude + data | Headlines only, 3–5 per category: Business, Tech, World, Pop culture, Sports (tag pills). Sports ends with the score card. |
| 8 | Off the clock | Claude | 2–3 short leisure items (ski, outdoors, cars, AI tools, food), each with an emoji. |
| 9 | Meme roundup | data + Claude | Up to 6 images, no captions. Skipped if none. |
| — | Charts | Claude picks, code draws | Optional, under a Big read, Top 3, Holdings or Movers story. Max 3, usually 0–1. |

Target length: 1,600–1,900 words (weekend ~1,000).

---

## 6. Editorial rules

All of them live in `prompts/EDITORIAL.md`, which the task reads every morning. Why the no-repeat rule works the way it does: each run starts with no memory, and the Nov 27 issue re-ran 8 stories from Nov 26. The task now copies the plain text of the last two issues from Gmail into `run/previous.json`, and render.py (`brief/previous.py`) blocks repeated links and near-identical headlines and warns on reworded ones. Gmail instead of a history file in the repo, because the task's ability to push to GitHub is still unconfirmed (§12).

---

## 7. Data files

`brief/schema.py` defines all three: `data.json` (collectors), `calendar.json` (Claude, from the connector; classification rules in TASK.md step 3) and `content.json` (Claude: text and links only, no HTML, no markdown). render.py enforces: allowed domains only, URLs unique across the issue, no repeats from the last two issues, memes and movers only from data.json, word caps (warn, then trim list ends), percentages in prose checked against data.json and charts, paragraphs of at most 6 phone lines, and the 95KB size limit (Gmail clips at ~102KB).

---

## 8. The scheduled task

Prompt: a short wrapper that points to `prompts/TASK.md`. The routine's own prompt also restricts Gmail to TASK.md's feedback and past-issue searches; update it whenever TASK.md adds a Gmail use. Connectors: Google Calendar and Gmail only. Cloud environment "the-7am": network access **Full**; `FINNHUB_API_KEY` and `RESEND_API_KEY` are plain environment variables. Setup steps are in `SETUP.md`.

---

## 9. Email template

`templates/email.html.j2` follows `DESIGN_SYSTEM.md` and reads colors from `brief/tokens.py`. The rendered sample issues (`python -m brief.run --fixture` → `run/preview*.html`; `python tests/screenshots.py` for 390px and 640px, light and dark) are the visual reference. Icons are inline attachments (`src="cid:<name>"`), only the ones the issue uses. Table layout, inline styles, system font stack, 400/500 weights only, memes as hotlinked images, plain-text version always included.

## 10. Sending

- Resend, account w0skinner@gmail.com. `from: "The 7AM <7am@wilsonskinner.com>"`. wilsonskinner.com was verified on Nov 27, 2026 (DNS at Porkbun: DKIM `resend._domainkey`, CNAMEs `send` and `rsend`, `_dmarc` p=none). Open and click tracking are off. Before that, issues came from `onboarding@resend.dev`, whose forced click tracking broke links.
- Icons in the `attachments` array with a `content_id`. Confirmed in Gmail iOS, light and dark.
- `reply_to: config.feedback_address`, so Reply in Gmail files feedback (§10b).
- Subject from content.json, no prefix. Sent immediately, never `scheduled_at`.
- One send per date: the Idempotency-Key is the date. `--test` uses a one-off key.

## 10b. Feedback loop

Wilson gives feedback by replying to the issue. No feedback section or button.

1. Every issue has `reply_to: w0skinner+7am-feedback@gmail.com`. Gmail delivers `+something` addresses to the normal inbox.
2. Each morning, before writing, the task searches Gmail for exactly `to:<feedback_address> from:me`. Read only.
3. `python -m brief.feedback` adds each new reply to the top of `feedback/FEEDBACK.md`: date, the issue's subject, the note with the quoted original removed, and the Gmail id in an HTML comment so nothing is filed twice.
4. The task commits and pushes **only** `feedback/FEEDBACK.md` (plus `data/sp500.csv` on the 1st of the month).
5. Feedback isn't acted on automatically. In a Claude Code session, Claude reads it, proposes fixes and marks entries done (`- [x]`).

Replies sent after 6:28am are picked up the next morning. Run `git pull` in `~/code/the-7am` to see new entries.

---

## 11. Decisions

- On Tuesdays, WTD equals 1D (the week is one day old). No special case.
- Monday covers only what happened since Sunday's issue (news and sports).
- Earnings "After hrs" is the latest extended-hours price vs the reporting day's close, for every reporter, including ones that reported before the open.
- "Reported yesterday" means the previous trading day.
- The big temperature in Your day is the current East Village temperature when the task runs.
- Market caps live in `data/sp500.csv` (refreshed monthly), not looked up live. The task refreshes it on the 1st and pushes it.
- Subway alerts and calendar events show on weekends too, when there are any.
- Earnings covers the top 200 S&P 500 companies plus holdings. If the email nears 95KB in peak season, cap the table with an "and N others" line (ask Wilson first).
- Off the clock may link leisure sites beyond the news allowlist (`sources.off_the_clock_extra`); render.py allows them only there.
- NYC today owns the city (events, big NYC sports news, city news); Off the clock is leisure outside it. Never the same item in both.
- Every link reads as the outlet name ("WSJ ↗"), never the article title.
- Google Calendar birthdays are ordinary all-day events on the primary calendar; the title rule catches them.
- Claude's web search can't filter to WSJ, NYT, Reuters, AP, BBC, FT or The Verge, and the fetcher can't open them; EDITORIAL.md says how to cite them anyway.
- Reddit never approved API access (Nov 26, 2026); memes come from Short Squeez, Exec Sum and Lemmy. Reddit code stays in case it's approved.
- Wilson doesn't use a Gmail filter, and declined rotating the Resend API key (free account, low stakes).

## 12. Open items

- **Confirm the task can push to GitHub.** Wilson replies to the Nov 28 issue; on Nov 29 check that it landed in `feedback/FEEDBACK.md`. If the task can only push to its own branch, use one long-lived `feedback` branch.
- **Drop the old sender from the past-issues search** in TASK.md step 1a after Dec 2, 2026, once both saved issues come from `7am@wilsonskinner.com`.
- **Sender avatar (optional).** Gmail's inbox circle comes from the sender address. Create a free Google Account for 7am@wilsonskinner.com (Porkbun email forwarding receives Google's code) and set `brand/7am-twotone.png` as its photo. BIMI needs a paid certificate, so it's out.
- **Name.** "The 7AM" is a working name; it's `brand.name` in config.yaml.
