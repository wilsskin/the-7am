# CLAUDE.md

Always read `DESIGN_SYSTEM.md` before making any visual change, and `BUILD_PLAN.md` before changing how the pipeline works.


## Architecture

A Python script and a Claude scheduled task, nothing else. Every morning at 6:28am ET the scheduled task clones this repo, runs `python -m brief.collect` (exact numbers from free data sources), files any new feedback replies from Gmail into `feedback/FEEDBACK.md`, reads Wilson's Google Calendar through the connector, writes the stories into `run/content.json`, draws any supporting charts with `python -m brief.charts`, then runs `python -m brief.render` and `python -m brief.send`. The email sends the moment the run finishes, usually around 6:35am ET. (It used to be held for 7:00 with Resend's scheduled_at, but Resend can't schedule emails with attachments, so those sends never arrived.) No servers, no database, no paid APIs, no Anthropic API key.

Code owns anything that must be exact (prices, earnings, weather, scores, layout). Claude owns anything that needs judgment (which stories, how to summarize them). Claude never writes HTML and never writes a number that isn't in `run/data.json`.

## Design

The 7AM is a sibling of wilsonskinner.com: same tokens, same grayscale restraint, one theme color. It uses the system font (SF Pro on Apple devices) instead of the site's Inter, because Gmail doesn't load web fonts. The full design system lives in `DESIGN_SYSTEM.md`, and the three `templates/reference_*.html` files (weekday, Monday, weekend) are the visual source of truth. When this repo's design system is silent, follow the portfolio's DESIGN_SYSTEM.md.

## How to work with Wilson

- **Prefer simple solutions.** Plain Python and a handful of small libraries. No frameworks, no extra services, nothing that costs money.
- **Offer options with tradeoffs** when there's more than one reasonable approach. Don't just pick one silently.
- **Ask rather than guess** on any implementation detail that isn't obvious. Wilson prefers a quick question over an assumption that needs to be undone.
- Wilson is not an experienced engineer, so explain the reasoning behind technical decisions clearly. Explain anything involving APIs, keys, git or deploys from scratch.

## Data source notes (verified Nov 22, 2026)

- ESPN's scoreboard rejects date ranges (`dates=A-B` returns 400). `brief/collect/sports.py` asks one date at a time.
- Claude's web search can't filter to WSJ, NYT, Reuters, AP, BBC, FT or The Verge, and the fetcher can't open them. EDITORIAL.md says how to cite them anyway.
- Memes (Wilson's choice, Nov 26, 2026), up to 6 a day, from `memes.sources` in config.yaml: Short Squeez's "Memes of the Day" (homepage, then the issue page; posted ~4am ET, skips `/p/insiders-*`), Exec Sum's "Meme Cleanser" (litquidity.co WordPress API, category 1; posted ~7am ET, so it's usually yesterday's issue), and Lemmy (`lemmy.world/api/v3/post/list`, no key) to fill. Newsletter issues count only if under 26 hours old, so nothing repeats. Each source can fail alone. If either newsletter redesigns, `section_images()` finds nothing and Lemmy covers. Reddit has required manual API approval since Nov 2025 and blocks requests without a key (403/429); its code stays, add "reddit" to `sources` if it's ever approved. Ruled out: X (reading costs ~$200/mo), Instagram (Meta App Review, hashtags only), Imgflip (blank templates only), 9GAG (no official API), Bluesky (public search needs login).
- Charts (Wilson, Nov 27, 2026): optional, only when they support a story. Claude names the data in a story's `chart` field; `python -m brief.charts` fetches it from Kalshi, Polymarket, BLS or Yahoo (all free, no key) and draws a PNG with matplotlib, attached inline like the icons. `--search "words"` finds Kalshi/Polymarket markets. FRED's CSV timed out from Wilson's Mac, so it isn't used. BLS never published October 2025 CPI, so year-over-year CPI has a gap there.
- No repeats (Nov 27, 2026): the task saves the last two issues' plain text from Gmail to `run/previous.json` (TASK.md step 1a); `brief/previous.py` + render.py block repeated links and headlines. Plain text, because Resend's click tracking rewrites the HTML links.
- Emoji: Gmail on the web (computer browser) redraws every emoji in Google's style; nothing in the email can stop that. The Gmail iPhone app and Apple Mail show Apple's (confirmed by Wilson, Nov 27, 2026). Not a bug.
- Weather: Open-Meteo first; on any failure, the National Weather Service (`api.weather.gov`, points → forecastHourly, plus the daily forecast for today's high). Open-Meteo returned 429 Too Many Requests on Nov 27, 2026: its free limit is per IP and the cloud task shares IPs. `data.json` weather `source` says which one answered.
- Setup steps only Wilson can do are in `SETUP.md`.

