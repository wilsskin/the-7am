# The 7AM: Build Plan

Handoff spec for a Claude Code agent. Read `CLAUDE.md` first, then all of this file (including §14, known risks and open items), `DESIGN_SYSTEM.md` and the three `templates/reference_*.html` mockups (open them in a browser), before writing any code. The design is final and approved by Wilson as of Nov 22, 2026: build it as specified, and ask before changing anything visual.

The 7AM is a sibling of Wilson's portfolio ([wilsskin/wms-portfolio](https://github.com/wilsskin/wms-portfolio)). It should feel like the same brand: same design tokens, same plain-spoken voice, same "simple over clever" engineering. When in doubt, look at how the portfolio does it.

**Constraint: this must run at no cost beyond Wilson's Claude plan.** No Anthropic API key, no paid APIs, no paid hosting. Every service below is on a free tier.

Owner: Wilson (w0skinner@gmail.com). Goal: *The 7AM*, a personal, ad-free morning newsletter emailed to Wilson every day at 7:00am ET, modeled on Exec Sum and Morning Brew, built around his holdings, his calendar and his interests.

## 0. How to work on this project

These come from the portfolio's CLAUDE.md and apply to every step here.

- **Prefer simple solutions.** Plain Python, few dependencies, no frameworks, no extra services. If a library saves ten lines, it probably isn't worth adding.
- **Offer options with tradeoffs** when there's more than one reasonable approach. Don't pick one silently.
- **Ask rather than guess** on anything not obvious. Wilson prefers a quick question over an assumption that has to be undone.
- **Explain your reasoning.** Wilson is a designer who builds, not an experienced engineer. Explain APIs, keys, git, cron and the scheduled task setup from scratch, in plain words.
- **Show, don't describe.** Each milestone ends with something Wilson can look at: a JSON file, a screenshot, an email in his inbox.
- **Never spend money.** If something seems to need a paid service or the Anthropic API, stop and ask.

---

## 1. Architecture

One GitHub repo, run daily by a **Claude cloud scheduled task**.

Code owns the parts that must be exact. Claude owns the parts that need judgment.

| Layer | Owner | Why |
|---|---|---|
| Market prices, earnings numbers, weather, subway alerts, scores, meme candidates | Python collectors (deterministic) | Numbers must never come from an LLM reading articles |
| Calendar events + birthdays | Claude, via the Google Calendar connector | Connector already authorized, no OAuth setup |
| Feedback (Wilson's replies) | Claude, via the Gmail connector, read only | Files replies into `feedback/FEEDBACK.md` (§10b) |
| Story selection, summaries, headlines, links | Claude, using web search | Needs editorial judgment |
| Layout | Jinja2 HTML template in the repo | Identical layout every day; Claude never writes HTML |
| Sending | Resend API | Reliable delivery to Gmail, free tier |

### Daily run (scheduled task)

1. Task fires at **6:22am ET** (`CRON_TZ=America/New_York 22 6 * * *`). Off the hour on purpose: on-the-hour runs can start late.
2. Claude Code clones the repo, files any new feedback replies (§10b), then runs `python -m brief.collect` → writes `run/data.json`.
3. Claude reads today's calendar through the connector → writes `run/calendar.json`.
4. Claude follows `prompts/EDITORIAL.md`, researches the news with web search, writes `run/content.json` matching `brief/schema.py`.
5. `python -m brief.render` validates both JSON files, enforces rules (dedupe, word caps, allowlist), renders `run/issue.html` + plain-text fallback.
6. `python -m brief.send` sends via Resend, scheduled for 7:00am ET (`scheduled_at`) if it's earlier than that, otherwise immediately.

### Failure rules (non-negotiable)

- If a collector fails, its section renders "Data unavailable this morning." Never fill numbers from search.
- If content.json fails validation, Claude gets one retry to fix it. If it still fails, render with whatever sections are valid.
- If render fails completely, send a plain-text email with whatever exists plus the error.
- The email always sends. A missing section is fine. A missing email is not.

---

## 2. Repo layout

```
the-7am/
  CLAUDE.md                 # provided: architecture, design, how to work with Wilson
  README.md                 # provided: portfolio-style project summary
  BUILD_PLAN.md             # this file
  DESIGN_SYSTEM.md          # provided: tokens, text styles, components, section layouts
  build_reference.py        # provided: generates the three reference issues from the tokens
  config.yaml               # all personal settings (see §3)
  prompts/
    TASK.md                 # the scheduled task prompt (see §8)
    EDITORIAL.md            # section rules, sources, style (see §6)
  brief/
    collect/
      markets.py            # indices, crypto, holdings, standout stock
      earnings.py           # yesterday's results + surprise %, next trading day's reporters, Monday week calendar
      market_calendar.py    # trading day, closures, early closes
      weather.py
      mta.py
      sports.py             # last night's scores for followed teams, Monday: this week's games
      memes.py
    tokens.py               # the DESIGN_SYSTEM.md tokens as one Python dict (port from build_reference.py)
    schema.py               # pydantic models for data.json, calendar.json, content.json
    render.py
    send.py
    run.py                  # local orchestrator: --dry-run, --fixture
  templates/
    reference_issue.html    # provided: weekday mockup, the visual source of truth
    reference_monday.html   # provided: Monday mockup
    reference_weekend.html  # provided: weekend mockup
    icons/                  # provided: six 60px PNG line icons (weather, subway, calendar)
    email.html.j2           # built by converting the reference mockups to Jinja (one template, edition switches)
    email.txt.j2
  data/
    sp500.csv               # ticker, name; refresh monthly
  feedback/
    FEEDBACK.md             # Wilson's replies to the issue, newest first (§10b)
  tests/
    fixtures/               # sample data.json, calendar.json, content.json
  run/                      # gitignored, per-run output
```

Python 3.12. Dependencies, kept deliberately short: `yfinance`, `exchange_calendars`, `requests`, `pydantic`, `jinja2`, `pyyaml`, `pytest` (Playwright for screenshot checks in dev only). No CSS inliner: the Jinja macros write inline styles from `tokens.py`. No Resend SDK: one `requests.post` call. Ask Wilson before adding anything else.

Local dev note: clone the repo outside iCloud Drive (e.g. `~/code/the-7am`). iCloud syncing a `.git` folder causes corruption.

---

## 3. config.yaml

```yaml
brand: { name: "The 7AM" }          # working name, Wilson may rename
recipient: w0skinner@gmail.com
feedback_address: w0skinner+7am-feedback@gmail.com   # Reply-To on every issue (§10b)
timezone: America/New_York
send_time: "07:00"
location: { name: "New York", lat: 40.7306, lon: -73.9866 }   # East Village
subway_lines: ["4", "5"]

markets:
  indices:
    - { symbol: "^GSPC", label: "S&P 500" }
    - { symbol: "^IXIC", label: "Nasdaq" }
    - { symbol: "SOXX",  label: "SOXX" }
  crypto:
    - { symbol: "BTC-USD", label: "Bitcoin" }
    - { symbol: "ETH-USD", label: "Ether" }
  holdings: ["GOOGL", "PLTR", "GEV", "COST", "V", "GS"]
  standout_min_market_cap: 100_000_000_000
  big_earnings_universe: top_50_sp500_by_market_cap   # plus holdings

sports:
  teams:
    - { league: nfl, team: "San Francisco 49ers" }
    - { league: nba, team: "Golden State Warriors" }
    - { league: mlb, team: "San Francisco Giants" }
  also_cover: ["NFL major headlines and trades", "NBA major headlines and trades"]

memes:
  subreddits: ["wallstreetbets", "ProgrammerHumor", "memes"]   # Wilson will tune
  count: 4

sources:
  subscribed: ["wsj.com", "nytimes.com"]          # prefer these links
  allowed: ["wsj.com", "nytimes.com", "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk",
            "nbcnews.com", "cnbc.com", "axios.com", "theverge.com", "techcrunch.com",
            "espn.com", "variety.com", "hollywoodreporter.com", "gothamist.com", "ny1.com",
            "ft.com", "bloomberg.com"]
  paywalled_unsubscribed: ["ft.com", "bloomberg.com"]   # link only if no other source has it
```

---

## 4. Data sources (collectors)

Verify each endpoint at build time. Free tiers and unofficial endpoints change. If one is dead, pick the closest free equivalent and note it in CLAUDE.md.

| Data | Source | Notes |
|---|---|---|
| Index, ETF, crypto, holdings prices | `yfinance` | Price at the last 4pm ET close, 1-day % (vs the 4pm ET close before it), week-to-date % (vs the 4pm ET close of the prior week's last trading day). Monday: YTD % instead of WTD. **Crypto uses the same 4pm ET snapshots as stocks, not a rolling 24h window**: pull hourly bars and take the bar at 16:00 ET on the same dates the stock closes come from. Weekend: crypto as of 4pm ET Friday. |
| Standout stock | `yfinance` over `data/sp500.csv` | Biggest absolute 1-day % move among names over $100B market cap. Return ticker, name, % move. Claude writes the 2–3 sentence "why" and finds a link. |
| Earnings results + calendar | Finnhub `/calendar/earnings` (free key) | EPS est/actual, revenue est/actual, timing (bmo/amc). Filter to the big universe. Code computes the surprise % for each: (actual − estimate) / |estimate|, rounded to 0.1% (positive = beat, negative = miss). After-hours / premarket move from `yfinance` (prepost). Also return the big-universe companies reporting the next trading day (company names); on Tue–Fri render.py appends "Deere reports tomorrow." / "Dell and Salesforce report tomorrow." (Friday: "report Monday") to the Earnings description. Nobody → no sentence. |
| Market closures / early closes | `exchange_calendars` (XNYS) | Any closure or early close today or later this week → a fixed sentence ("Markets close Thursday for Thanksgiving, early close Friday at 1pm.") that render.py appends to the Before the bell description. |
| Weather | Open-Meteo `/v1/forecast` (no key) | High/low °F, conditions, hourly precip probability → "rain likely after 4pm". The WMO weather code also picks the icon: `sun` (0–1), `cloud` (2–48), `rain` (51–67, 80–82, 95–99), `snow` (71–77, 85–86). |
| Subway alerts | MTA GTFS-RT alerts JSON (`api-endpoint.mta.info`, camsys subway-alerts feed, no key) | Active alerts where informed entity route is 4 or 5. Header text only, max 2. |
| Last night's scores | ESPN public scoreboard JSON (`site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard`) | Only followed teams, only games that finished since the previous morning's run (Monday too: since Sunday's run). One request per date; ESPN rejects date ranges. Return W/L, both scores, league. |
| This week's games (Mondays) | ESPN team schedule JSON (`site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams/{team}/schedule`) | 49ers and Warriors games Monday through Sunday: day, opponent, home/away, start time ET. |
| Meme candidates | Reddit API (script app, OAuth) | Top of day, image posts only, `over_18 == false`, score threshold. Return ~12 candidates with image URLs. Claude picks the final 4 (§6). |

`data.json` must include `as_of` timestamps per block and an `ok: true/false` flag per collector.

---

## 5. Sections (final, in order)

Day variants (each has a reference file, see DESIGN_SYSTEM.md):
- **Mon** (`reference_monday.html`): YTD instead of WTD in the market and holdings cards. Your day card adds a "This week" calendar preview (Tue–Sun events). Earnings shows "Reporting this week" (one row per day, company names only) instead of "Reported yesterday". The sports card adds this week's 49ers and Warriors games.
- **Tue–Fri** (`reference_issue.html`): standard.
- **Sat/Sun** (`reference_weekend.html`): Before the bell becomes "Markets" with Bitcoin and Ether only (4pm ET Friday). No Holdings, no Earnings, no "On deck today". Everything else stays.
- **Holiday / early close:** a weekday issue. The Before the bell description ends with the closure sentence (no callout box) whenever the market is closed or closes early any day this week.

Every section has a header: label plus a one-line description Claude writes that morning (`section_desc` in content.json).

| # | Section | Source | Spec |
|---|---|---|---|
| 1 | Subject line + intro | Claude | Subject: punchy hook from the top story, Exec Sum style, under 60 chars. Intro: 2–5 sentences, aim for 3. The first sentence is the one thing to know today. |
| 2 | Your Day | data.json + calendar.json + Claude | Weather line. Subway alerts for 4/5 if any. Today's calendar events (time + title). Birthdays: any event today whose title contains "birthday" (case-insensitive) or eventType BIRTHDAY → "Lily Bien's birthday 🎂". Event titled "Happy birthday!" is Wilson's own birthday → render a special greeting. US holidays from the holidays calendar. Monday only: "This week" preview of the rest of the week's events. Then "Around NYC": 1–2 linked NYC news items that affect his day (transit, weather, city news). An empty calendar is simply left out; never mention that it's empty. |
| 3 | Before the Bell | data.json + Claude | One market card: S&P 500, Nasdaq, SOXX, Bitcoin, Ether (price at 4pm ET close, 1D %, WTD % or YTD %). Standout: "NVDA −6.40%" on one line (no "Standout" label), then Claude's 2–3 sentence why, with a link. "On deck today": econ releases, Fed speakers, notable events (Claude, from search). |
| 3b | Earnings | data.json | Right after Before the Bell, ahead of Holdings. Table of yesterday's big reporters: Revenue and EPS each on one line as the actual plus the surprise vs estimate in colored parentheses ("57.0B (+3.3%)"), and the after-hours move. Numbers only, no notes. No "Reporting today" on weekdays. Mondays: "Reporting this week" instead, one row per day with company names only (no tickers, no before/after timing). Skip the section if empty. |
| 4 | Your Holdings | data.json + Claude | One row per holding (price, 1D %, WTD % or YTD %). Then a story (2–3 sentences, linked) for **every** holding with relevant, recent news in the last 24h. No cap: on a big day, cover them all. Headline starts with the ticker ("PLTR: Army expands its software contract"). No news → no story. Never pad. |
| 5 | The Big Read | Claude | Single most important story. ~300 words, 3–4 short paragraphs, Morning Brew structure and length. Tone: clear, concise, direct. Not jokey. Ends with a link. |
| 6 | Top 3 | Claude | 3 more big stories, ~100 words each, headline + paragraph + link. |
| 7 | The Latest | Claude + data.json | Headlines only, one line each, linked, 3–5 per category, in this order: **Business** (deals, Wall Street, Goldman; keep to 3), **Tech**, **World/Politics**, **Pop Culture**, then **Sports** last. Each category label is a tag pill. Sports: headlines first, then the score card from data.json below them (last night's results; Mondays also this week's 49ers/Warriors games; no results and not Monday → no card). Sports headlines: 49ers, Warriors, Giants news, big NFL/NBA headlines and trades, and major NFL injuries (starters out for multiple games or the season). |
| 8 | Off the Clock | Claude | 2–3 brief items, rotating: ski conditions (Nov–Apr, Northeast + Tahoe), things to do in NYC this week, outdoors/backpacking, cars (Rivian etc.), AI tools. Short. Topic goes at the start of the headline ("Ski report: Killington opens more terrain"), no eyebrow. |
| 9 | Meme Roundup | data.json + Claude | 4 images, Exec Sum style, no captions needed. |

Global target: 1,600–1,900 words (weekend ~1,000).

---

## 6. Editorial rules (put these in prompts/EDITORIAL.md)

**Each story appears once.** Priority order for placement: Big Read > Top 3 > Holdings > Earnings > Before the Bell > The Latest > Around NYC > Off the Clock. render.py enforces this by URL and by near-duplicate headline check, and drops the lower-priority duplicate.

**Around NYC vs Off the Clock.** Around NYC is news that affects Wilson's day: transit, weather, city government, things happening today. Off the Clock is leisure: events to go to, ski, outdoors, cars, AI tools. An NYC event belongs in Off the Clock unless it changes his commute or plans today. Never the same item, venue or event in both.

**Section descriptions.** One line (two at most) under every section label, summarizing that section today: "Nvidia beat on both lines and still fell after hours. Walmart missed on revenue." Concrete, not generic ("Here are today's headlines" is not allowed). Any number must come from data.json. Don't repeat the closure line in Before the bell or the next-reporters line in Earnings; render.py adds both.

**Holdings news.** Cover every holding with relevant, recent news, with no cap. Relevant means it could move the stock or changes the story around it: earnings, guidance, deals, contracts, regulation, executive changes, big product launches, analyst moves on the name. Skip passing mentions and listicles.

**Sports.** Besides team news and big trades, include major NFL injuries: a starter out for multiple games or the season, especially quarterbacks and anyone on the 49ers.

**Intro.** 2–5 sentences, aim for 3. The first sentence is the hook and also becomes the inbox preview. Don't spend a sentence on the calendar; if the calendar is empty, say nothing about it.

**Sources.** Only domains in `config.sources.allowed`. Prefer WSJ and NYT links when they cover the story (Wilson subscribes). Use FT or Bloomberg only if no other allowed source has it. Every item has a link to the actual article, not a homepage. Never invent a URL; if an article can't be found, drop the item.

**Recency.** News from the last ~24 hours (since the previous 7am issue). Monday covers only what happened since Sunday's issue (decided Nov 22, 2026).

**Selection.** Pick what a sharp 23-year-old in NYC finance and product design needs to know to sound informed at work and with friends. Big market movers, big tech/AI, major world news, NYC things that affect his day. Skip celebrity filler, clickbait and opinion pieces posing as news.

**Style.** Write like wilsonskinner.com: short declarative sentences, one idea each, specific numbers ("increasing applications by 35%"), strong verbs over adjectives. Clear and direct, never jokey. No em dashes, no exclamation points, no filler ("amid," "in a move that," "it remains to be seen," "leverage," "impactful"). The subject line and intro can have some edge, like Exec Sum. Headlines are statements with a verb, never questions or puns.

**Accuracy.** Do not state any price, percentage or EPS number in prose unless it comes from data.json. Claude may explain why something moved; the numbers come from the collectors.

**Summaries are paraphrased.** Never copy article text. Short summaries in Claude's own words with a link out.

**Memes.** From the candidates in data.json, pick 4 that are funny, not political, not offensive, not NSFW, ideally finance/tech flavored. Claude should view the images before picking.

---

## 7. content.json schema (pydantic, brief/schema.py)

Claude writes text and links only. No HTML, no markdown.

```python
class Link(BaseModel):
    title: str
    url: HttpUrl
    source: str                    # "WSJ", "NYT", "Reuters"...

class Story(BaseModel):
    headline: str
    body: str                      # plain text, paragraphs split by \n\n
    link: Link

class Content(BaseModel):
    date: date
    edition: Literal["weekday", "monday", "weekend", "holiday"]
    subject: str = Field(max_length=70)
    intro: str                              # 2-5 sentences, aim for 3
    section_desc: dict[Literal["your_day","before_the_bell","earnings","holdings","big_read",
                               "top_3","latest","off_the_clock","memes"], str]   # one line each
    your_day_nyc: list[Link]                # 0-2, rendered under "Around NYC"
    standout: StandoutStory | None          # {body, link}; headline is built by code ("NVDA −6.40%")
    on_deck_today: list[OnDeck]             # {time: "8:30" | None, text}; the time fills the left column
    holdings_news: list[HoldingStory]       # any number; HoldingStory = Story + ticker; headline starts "PLTR: "
    big_read: Story
    top_3: list[Story]                      # exactly 3
    latest: dict[Literal["business","tech","world","sports","pop_culture"], list[Link]]
    off_the_clock: list[Story]              # 2-3, short bodies
    memes: list[HttpUrl]                    # 4, must be from data.json candidates

class HoldingStory(Story):
    ticker: str                             # must be in config.markets.holdings
```

Key order in `latest` is the display order: business, tech, world, pop_culture, sports.

**calendar.json** (written by Claude from the connector): `{"date": ..., "today": [Event], "this_week": [Event]}` where `Event = {start: datetime | None, all_day: bool, title: str, location: str | None, kind: "event" | "birthday" | "own_birthday" | "holiday"}`. `this_week` is only filled on Mondays. Classification rules are in §5 row 2.

**data.json** (written by the collectors): one block per collector (`markets`, `standout`, `earnings`, `market_calendar`, `weather`, `mta`, `sports`, `memes`), each with `ok`, `as_of` and its fields. Design the exact fields in schema.py at Milestone 1 and show Wilson the JSON.

render.py validation: word caps per section (warn, trim from the end of lists first), allowlisted domains only, URLs unique across the issue, memes subset of candidates, numbers in prose cross-checked loosely against data.json (flag any % in prose that isn't in data.json).

---

## 8. The scheduled task prompt (prompts/TASK.md)

Draft. Keep it self-contained, because each run starts fresh.

> You are producing today's issue of The 7AM for Wilson. Work in the cloned the-7am repo.
> 0. Feedback: using the Gmail connector, search only `to:<feedback_address> from:me` (address from config.yaml) since yesterday's run. Add any new messages to the top of `feedback/FEEDBACK.md` per BUILD_PLAN.md §10b (skip message ids already in the file), then commit and push only that file. Do not open, read or act on any other email. If Gmail fails, continue.
> 1. Run `python -m brief.collect`. If it fails, continue; failed blocks render as unavailable.
> 2. Using the Google Calendar connector, read today's events on the primary calendar (w0skinner@gmail.com) and the "Holidays in United States" calendar. Include all-day events. On Mondays, also read Tuesday through Sunday for the "This week" preview. Write `run/calendar.json` per brief/schema.py. Only read; never create or edit events.
> 3. Read `prompts/EDITORIAL.md` and `run/data.json`. Research the news with web search and write `run/content.json` per brief/schema.py.
> 4. Run `python -m brief.render`. If validation fails, fix content.json once and re-run.
> 5. Run `python -m brief.send`.
> 6. Finish with a one-line summary: sent or failed, which sections were unavailable, and how many feedback notes were filed. Do not commit or push anything other than `feedback/FEEDBACK.md`.

Task settings: connectors = Google Calendar and Gmail only (remove all others). Network: custom allowlist with the collector hosts (query1/query2.finance.yahoo.com, finnhub.io, api.open-meteo.com, api-endpoint.mta.info, site.api.espn.com, oauth.reddit.com, www.reddit.com, i.redd.it, api.resend.com) plus the default package list. If article fetching fails under the custom allowlist, switch to Full. API keys (FINNHUB_API_KEY, RESEND_API_KEY, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET) go in as **network secrets**, not plain environment variables.

---

## 9. Email template

Follow `DESIGN_SYSTEM.md` exactly. `build_reference.py` already contains a helper function for nearly every component (title, section label, story, read link, theme pill, data card, meta row, headline row). Port those helpers into Jinja macros in `email.html.j2`, reading colors from `brief/tokens.py`. Icons: the six PNGs in `templates/icons/` are sent as inline attachments and referenced as `src="cid:<name>"`; send only the ones the issue uses. Do not design from scratch. Match the reference file for each edition (`reference_issue.html`, `reference_monday.html`, `reference_weekend.html`) at 390px and 640px wide, light and dark. Key constraints, all in DESIGN_SYSTEM.md (Email Engineering Rules): table layout, inline styles, system font stack (no web fonts), 400/500 weights only, HTML under 100KB, memes as hotlinked images, plain-text alternative always included.

## 10. Sending

- Resend. Wilson signs up with w0skinner@gmail.com. Without a verified domain, Resend only sends from its test address to the account's own email, which is exactly this use case. Verify this at build time. A custom domain can come later.
- `from: "The 7AM <onboarding@resend.dev>"` until a domain is verified.
- Icons go in the `attachments` array with a `content_id` (inline images). Verify at build time that Resend supports this and that Gmail iOS shows them; if not, fall back to hosting the PNGs at a public https URL and ask Wilson where.
- `reply_to: config.feedback_address`, so hitting Reply in Gmail sends feedback without typing an address (§10b).
- Subject line comes from content.json (`subject`), no prefix.
- Use `scheduled_at` = 7:00 ET when the run finishes early.
- Wilson should add a Gmail filter: never send to spam, mark important.

## 10b. Feedback loop

Wilson gives feedback by replying to the issue. There is no feedback section or button in the email; Wilson knows to reply. The goal: his notes end up in a file in the repo (`feedback/FEEDBACK.md`, newest first, dated, tagged with the issue they reply to) so a Claude Code session can read it and fix things.

**Pipeline: reply to the email (decided Nov 22, 2026).**

1. Every issue is sent with `reply_to: config.feedback_address` (`w0skinner+7am-feedback@gmail.com`). Gmail delivers anything sent to a `+something` version of an address to the normal inbox, so no new account or inbox is needed. Without this, Reply would go to `onboarding@resend.dev` and be lost.
2. Wilson hits Reply in Gmail and types his note. The reply's subject is "Re: <that day's subject>", so it's clear which issue it's about. Replying several times is fine; each reply is one entry.
3. Each morning, before writing the issue, the scheduled task searches Gmail through the Gmail connector for exactly `to:<feedback_address> from:me` since the last run. Read only: it never sends, labels, deletes or opens any other mail.
4. For each new message it adds an entry to the top of `feedback/FEEDBACK.md`: received date, the issue's subject (from "Re: ..."), the note text with the quoted original removed (drop everything from the "On ... wrote:" line down, and any lines starting with ">"), and the Gmail message id in an HTML comment so the same reply is never added twice.
5. The task commits and pushes **only** `feedback/FEEDBACK.md` with the message `Add feedback from <date>`. This is the one exception to "do not commit or push anything" in TASK.md.
6. Feedback is not acted on automatically. When Wilson opens a Claude Code session, Claude reads `feedback/FEEDBACK.md`, proposes fixes, and marks entries done (`- [x]`) once they ship.

Why this way: free, nothing to tap or set up beyond Reply, and the notes end up as a plain file in the repo. Tradeoff: the morning task gets Gmail read access, so the search is fixed to the feedback address from Wilson himself, and TASK.md says to read nothing else in the inbox. Replies sent after 6:22am are picked up the next morning. Verify at build time that Resend's `reply_to` survives into Gmail iOS's Reply.

Where the file lives: in the GitHub repo, because the cloud task can only save to GitHub, not to Wilson's Mac. The repo is cloned locally at `~/code/the-7am` (not the iCloud `projects/newsletter` folder, see §2). Run `git pull` there to see new entries.

---

## 11. Milestones

Work in this order. Each ends with something Wilson can see.

1. **Scaffold + collectors.** Create the repo at `~/code/the-7am` and copy in the provided files from Wilson's iCloud `projects/newsletter` folder: CLAUDE.md, README.md, BUILD_PLAN.md, DESIGN_SYSTEM.md, build_reference.py, the three templates/reference_*.html files and templates/icons/. Then config, tokens, schema, all collectors with tests. `python -m brief.collect` writes a real data.json. Show Wilson the JSON.
2. **Template + render.** Port the helpers in `build_reference.py` into macros in `email.html.j2` per DESIGN_SYSTEM.md, render it against fixture content.json. `python -m brief.run --fixture` writes `run/preview.html`. Screenshot it at 390px and 640px, light and dark (Playwright), compare against the reference, and show Wilson.
3. **Editorial pass.** Write EDITORIAL.md. In an interactive Claude Code session, do steps 2–4 of TASK.md by hand to produce a real issue. Show Wilson.
4. **Send.** Resend wired up; send a real test issue to Wilson's inbox. Check on iPhone Gmail, light and dark mode: icons show (inline attachments), layout matches the mockups, and tapping Reply addresses the feedback address.
5. **Schedule.** Create the scheduled task (TASK.md prompt, Google Calendar and Gmail connectors only, network allowlist, network secrets). Do a Run now. Reply to that issue once and confirm the reply lands in `feedback/FEEDBACK.md` the next morning.
6. **Shadow week.** Let it run 5 mornings. Collect Wilson's feedback, tune EDITORIAL.md and the template.

## 12. Things Wilson has to do himself

- Create the GitHub repo (private) and connect GitHub to Claude Code on the web.
- Create accounts and keys: Finnhub (free), Resend (free, sign up with w0skinner@gmail.com), Reddit script app.
- Approve the scheduled task and its network settings.
- Keep the Google Calendar and Gmail connectors connected.

## 13. Cost

$0 beyond Wilson's existing Claude plan. The scheduled task runs count against his plan usage like any other session. Finnhub, Open-Meteo, MTA, ESPN, Reddit, GitHub and Resend are all free at this volume. Do not add the Anthropic API or any paid service. If something seems to need one, stop and ask Wilson.

## 14. Known risks and open items

Read before Milestone 1. Each risk names its fallback; if the fallback isn't good enough, ask Wilson.

**Risks to verify early (Milestone 1 or 4)**
- **Yahoo Finance from the cloud.** `yfinance` is an unofficial scraper and Yahoo often rate-limits or blocks requests from cloud servers. Test it from the scheduled task's environment, not just locally. Fallbacks: Finnhub `/quote` (free key, stocks and ETFs; index values via SPY/QQQ only if Wilson agrees), Coinbase public API for the 4pm ET crypto price.
- **Reddit API access.** Reddit now reviews new API apps instead of approving them instantly, so a script app may not be granted. Decided (Nov 22, 2026): if access isn't granted, ship without the Meme roundup and add it once access comes through. Don't look for another meme source. The email must render fine with zero memes: skip the section entirely.
- **Resend inline images and reply_to.** Confirm both work in Gmail iOS (BUILD_PLAN §10, §10b). Inline-image fallback: host the PNGs at a public https URL (ask Wilson where).
- **Pushing from the scheduled task.** Confirm the cloud task can commit and push `feedback/FEEDBACK.md` to the default branch. If it can only push to its own branch, use one long-lived `feedback` branch, and tell Wilson to `git pull` that branch.
- **Connectors inside a scheduled task.** Confirm the Google Calendar connector can see the "Holidays in United States" and contacts "Birthdays" calendars, and that the Gmail connector can search. Wilson has to connect Gmail in claude.ai first (it isn't connected yet).
- **Gmail clipping.** Holdings news has no cap, so a big day can get long. Keep the rendered HTML under 95KB; if it goes over, shorten stories, not sections.
- **Memes from the cloud.** The task has to download and look at each meme image before picking. If it can't view images, pick by title and score and tell Wilson.

**Found at build time (Nov 22, 2026)**
- Yahoo, Open-Meteo, MTA, ESPN, Coinbase and the S&P 500 list all work from Wilson's Mac. ESPN's scoreboard rejects date ranges, so sports asks one date at a time. Cloud test still pending.
- Claude's web search refuses domain filters for WSJ, NYT, Reuters, AP, BBC, FT and The Verge (those sites block Anthropic's crawler), and the fetcher can't open them. Axios returns 403; Gothamist and Variety redirect bots to a paywall host. EDITORIAL.md says how to cite them anyway.
- Resend (Milestone 4 test, Nov 22): inline cid icons show in Gmail iOS, light and dark mode look right, and Reply goes to the feedback address. Feedback search and filing work end to end. But the shared onboarding@resend.dev sender adds click tracking (links rewritten via resend-clicks.com) and an open pixel, against "no tracking" in DESIGN_SYSTEM.md. Tracking is per domain and off by default on a verified domain, so the fix is sending from Wilson's own domain.
- Google Calendar: birthdays are ordinary all-day events on the primary calendar ("Lily Bien's birthday"); there is no separate Birthdays calendar. The title rule catches them.

**Decided (Nov 22, 2026)**
- On Tuesdays, WTD equals 1D (the week is one day old). Keep it as is; no special case.
- Monday covers only what happened since Sunday's issue (news and sports), not the whole weekend.
- Earnings "After hrs" is the latest extended-hours price vs the reporting day's close, for every reporter, including ones that reported before the open.
- "Reported yesterday" means the previous trading day.
- The big temperature in Your day is the current East Village temperature when the task runs.
- Market caps live in `data/sp500.csv` (refreshed monthly with `python -m brief.sp500`), not looked up live.
- Subway alerts and calendar events show on weekends too, when there are any.
- Crypto's 4pm price is the open of the 16:00 ET hourly bar (fallback: close of the 15:00 bar).
- The GitHub repo is created in Milestone 1 so the cloud Yahoo test can run early.
- Off the clock may link leisure sites beyond the news allowlist (`sources.off_the_clock_extra` in config.yaml); render.py allows them only there.
- The scheduled task refreshes `data/sp500.csv` on the 1st of each month and pushes it: the second exception to "only push FEEDBACK.md".
- Wilson's own birthday (theme pill in Your day) and "unavailable" states (a collector failed) aren't mocked up. Build them from the spec, render each with a fixture at Milestone 2, and show Wilson the draft.

**To do later (agreed Nov 22, 2026)**
- **Send from Wilson's own domain** (option A). Higher priority than it looked: on Nov 22 the resend-clicks.com redirect failed its TLS handshake, so tapped links in the email did not open (direct URLs all work). Verify wilsonskinner.com (or a subdomain) in Resend by adding the DNS records Resend gives, then change `sender` in config.yaml to something like `The 7AM <7am@wilsonskinner.com>` and update the Gmail filter. Why: the shared onboarding@resend.dev sender forces click and open tracking (links go through resend-clicks.com), which DESIGN_SYSTEM.md rules out; on a verified domain tracking is off by default. Confirm both tracking toggles are off in Resend → Domains afterwards.
- **Rotate the Resend API key**: the first key was pasted into a chat. Create a new one, delete the old one (ends in 24p2), update ~/.zshrc and the scheduled task's secret.

**Small decisions still open (ask Wilson when you reach them)**
- Plain-text version layout: derive it from the HTML order; show Wilson once.
- Meme subreddits and the final name ("The 7AM" is a working name) are Wilson's to tune any time.

