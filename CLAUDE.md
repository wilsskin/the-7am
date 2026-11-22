# CLAUDE.md

Always read `DESIGN_SYSTEM.md` before making any visual change, and `BUILD_PLAN.md` before changing how the pipeline works.


## Architecture

A Python script and a Claude scheduled task, nothing else. Every morning at 6:22am ET the scheduled task clones this repo, runs `python -m brief.collect` (exact numbers from free data sources), files any new feedback replies from Gmail into `feedback/FEEDBACK.md`, reads Wilson's Google Calendar through the connector, writes the stories into `run/content.json`, then runs `python -m brief.render` and `python -m brief.send`. The email lands at 7:00am ET. No servers, no database, no paid APIs, no Anthropic API key.

Code owns anything that must be exact (prices, earnings, weather, scores, layout). Claude owns anything that needs judgment (which stories, how to summarize them). Claude never writes HTML and never writes a number that isn't in `run/data.json`.

## Design

The 7AM is a sibling of wilsonskinner.com: same tokens, same grayscale restraint, one theme color. It uses the system font (SF Pro on Apple devices) instead of the site's Inter, because Gmail doesn't load web fonts. The full design system lives in `DESIGN_SYSTEM.md`, and the three `templates/reference_*.html` files (weekday, Monday, weekend) are the visual source of truth. When this repo's design system is silent, follow the portfolio's DESIGN_SYSTEM.md.

## How to work with Wilson

- **Prefer simple solutions.** Plain Python and a handful of small libraries. No frameworks, no extra services, nothing that costs money.
- **Offer options with tradeoffs** when there's more than one reasonable approach. Don't just pick one silently.
- **Ask rather than guess** on any implementation detail that isn't obvious. Wilson prefers a quick question over an assumption that needs to be undone.
- Wilson is not an experienced engineer, so explain the reasoning behind technical decisions clearly. Explain anything involving APIs, keys, git or deploys from scratch.
