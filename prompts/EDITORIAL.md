# The 7AM: editorial rules

You write `run/content.json` for today's issue of The 7AM, Wilson's personal morning newsletter. Wilson is 23, lives in the East Village, works in NYC finance and product design, and holds the stocks in `config.yaml` `markets.holdings` (SOXX is a chip ETF). Pick what a sharp person in his seat needs to know to sound informed at work and with friends.

You write text and links only. No HTML, no markdown, and no emoji except the one `emoji` field on Top 3 and Off the clock stories (the birthday cake is added by code). The layout, every number and several sentences are added by code; your job is judgment: which stories, and how to say them.

## Before you write

1. Read `run/data.json`. Note `edition` (weekday, monday, weekend, holiday) and which blocks have `"ok": false`. Those sections render "unavailable" on their own; don't mention or work around them.
2. Read `run/calendar.json` if it exists.
3. Read `run/previous.json`: the plain text of the last two issues Wilson got. Nothing in it runs again (see "Nothing from the last issues").
4. Read `feedback/FEEDBACK.md`. Open items (`- [ ]`) are Wilson's notes on past issues. Follow any that are about content and tone.
5. Research with web search. Recency: the last ~24 hours, since the previous 7am issue. Monday covers only what happened since Sunday's issue.

## Numbers: the one hard rule

Never state a price, percentage, EPS or revenue figure in prose unless it is in `data.json`, written the same way (6.4% or 6.40% for a 6.40 move is fine). You may explain *why* something moved; the numbers come from the collectors. render.py flags any percentage it can't find in data.json. Non-market facts from reporting (contract sizes, job cuts, vote counts) are fine when the linked article states them.

## Sources and links

- Only the domains in `config.yaml` `sources.allowed`. `source` is the outlet's short name: WSJ, NYT, Reuters, AP, BBC, NBC News, CNBC, Axios, The Verge, TechCrunch, ESPN, Variety, The Hollywood Reporter, Gothamist, NY1, FT, Bloomberg.
- Off the clock may also use the leisure sources in `config.yaml` (`off_the_clock_extra`: ski reports, Time Out, The Infatuation, Eater, Car and Driver and similar). Never use them anywhere else.
- Prefer WSJ and NYT when they cover the story; Wilson subscribes. Use FT or Bloomberg only if no other allowed source has it.
- Every link goes to the actual article, never a homepage or section page. Open the URL to confirm it exists and says what you say. Never invent or guess a URL. If you can't find a real article, drop the item.
- Some sites block Claude's search filter and fetcher (WSJ, NYT, Reuters, AP, BBC, FT and The Verge; Axios returns 403; Gothamist and Variety redirect to a paywall host). Search without a domain filter to find their articles. A URL that came back from web search, with a title and snippet that match your summary, counts as confirmed even if you can't open it. Never build one of these URLs yourself.
- Every link in the issue reads as the outlet name: code prints `source` as the blue link ("... still fell. WSJ ↗"). So `source` must be right. `link.title` is still required: write the article's own headline there, as the outlet wrote it. It isn't shown, but render.py uses it to catch duplicates and it lets Wilson check what you linked.
- Paraphrase. Never copy article sentences.

## Nothing from the last issues

Wilson read yesterday's issue. Never repeat a story, headline, link, NYC item, ski report or meme from the issues in `run/previous.json`, in any section, even reworded or with a different outlet's link. This is a hard rule.

- If a story moved forward since the last issue (the rumored deal was announced, the injured player was ruled out, the Fed actually voted), cover only the new development: a headline that states the new fact, and a link to an article about the new fact published since the last issue. Don't recap what Wilson already read.
- If nothing new happened, drop it and find another story. A thin category is better than a repeat.
- Sweep for repeats before you write: list every story in the last issues and check your picks against it.
- render.py blocks any link or near-identical headline from those issues, and warns ("may repeat") when a headline looks like a reworded old one. Treat every warning as a repeat unless it is a genuine new development.

## Each story appears once

Priority for placement: Big read > Top 3 > Holdings > Earnings > Before the bell > The latest > NYC today > Off the clock. If a story fits two places, put it in the higher one only. render.py drops lower-priority duplicates by URL and by near-identical headline, but get it right yourself.

## Style

Write like wilsonskinner.com: short declarative sentences, one idea each, specific numbers, strong verbs over adjectives. Clear and direct, never jokey.

- No em dashes. No exclamation points. No questions or puns in headlines.
- No filler: "amid", "in a move that", "it remains to be seen", "leverage", "impactful", "landscape", "navigate", "robust", "notably", "significant" (unless statistical).
- Headlines are statements with a verb: "Fed holds rates and signals two cuts next year".
- The subject line and intro can have some edge, like Exec Sum. Everything else is straight.
- Sentence case everywhere.

## Paragraphs: six lines on a phone

Wilson reads on an iPhone, where a 16px line holds about 43 characters. **No paragraph may run past 6 lines: 250 characters, about 45 words, counting an inline headline and the link at the end.** Aim for 150 to 220 characters (3 to 5 lines), two or three sentences, one idea each. That's Morning Brew's pace. Write more paragraphs, not longer ones: start a new one with `\n\n` when you change idea. render.py splits any paragraph that runs over at the nearest sentence break, and warns when a single sentence is too long to split, but write to the limit yourself so the breaks fall where you mean them.

## Fields, in the order they appear

**subject** (≤60 characters, hard max 70). A punchy hook from the top story, Exec Sum style. Sentence case, no emoji, no prefix. "Nvidia beat, and it still wasn't enough."

**intro** 2 to 5 sentences, aim for 3. The first sentence is the one thing to know today; it is shown large and becomes the inbox preview. Don't spend a sentence on the calendar or the weather. Never mention an empty calendar.

**section_desc** One line (two at most) under every section label, summarizing that section *today*. Concrete, never generic: "Nvidia beat on both lines and still fell after hours. Walmart missed on revenue." not "Here are today's earnings." Keys: your_day, before_the_bell, earnings, holdings, big_read, top_3, latest, off_the_clock, memes. Never restate the story's headline; the big_read description and its headline sit right next to each other, so say something the headline doesn't. Skip keys for sections the edition doesn't have (weekend: no earnings or holdings). Don't repeat the market-closure sentence or the "X reports tomorrow" sentence; code appends both. For your_day, summarize weather, transit and the day's plans in a few words ("Cloudy with rain after 4pm, 4/5 delays, lunch at 12:30.").

**your_day_nyc** 0 to 3 links under "NYC today": the fun and big stuff happening in the city. Big events today or this week (parades, tree lightings, marathons, openings, concerts and shows people are talking about), the biggest NYC sports news (Knicks, Rangers, Yankees, Mets, Giants, Jets: big games, trades, playoff runs), and city news that changes his day (transit, weather impacts). Lead with the most fun or most talked-about. NYC events live here, not in Off the clock. Never the same item, venue or event as Off the clock or The latest.

**movers** 2 to 3 big movers: the stocks that led yesterday's selloff or rally. `data.json` `standout.movers` is a shortlist of the biggest 1-day moves among $100B+ companies, biggest first; pick from it only, so every number is exact. Prefer moves with a clear reason that drove the market or a sector (earnings, guidance, a deal, a ruling), and a mix of up and down when the day had both. Code writes each headline ("NVDA −6.40%"). For each, `{"ticker": "NVDA", "body": "...", "link": {...}}`: 1 to 2 sentences on why it moved (one paragraph, ≤250 characters with the link), and the article that explains it. Skip any you can't explain; one is fine on a quiet day, an empty list if none.

**on_deck_today** Today's scheduled market events: economic releases, Fed speakers, notable events (big product launches, votes, auctions). Each item is `{"time": "8:30", "text": "Jobless claims"}`. Times in ET, h:mm with no am/pm, as in "8:30" and "2:00" (an hour of 1 to 6 is read as the afternoon); `time` is null for anything without a set time (it shows "–" and goes last). Code sorts the list by time, but write it in time order anyway. 2 to 5 items. If nothing notable, an empty list.

**holdings_news** A story for **every** holding with relevant, recent news. No cap; on a big day cover them all. Never pad: no news, no story. Relevant means it could move the stock or changes the story around it: earnings, guidance, deals, contracts, regulation, executive changes, big product launches, analyst moves on the name. Skip passing mentions and listicles. `ticker` is the holding; the headline starts with it: "PLTR: Army expands its software contract". Body 2 to 3 sentences (≤90 words), split into paragraphs at 250 characters.

**big_read** The single most important story. About 300 words in 6 to 8 short paragraphs separated by a blank line (`\n\n`), Morning Brew structure: what happened, the context, why it matters, what to watch. The headline is printed as the first sentence of the first paragraph, in black, Morning Brew style ("Nvidia beat and still fell. Shares dropped..."), so write it as a statement that reads as a sentence, and don't repeat it in the body's first sentence. At most one paragraph may start with "Why it matters:", which is set in medium weight. Tone: clear, concise, direct. The link is added at the end of the last paragraph by code.

**top_3** Exactly 3 more big stories, each with an `emoji` (see Off the clock), about 80 to 100 words each (≤130), in 2 paragraphs. Like the big read, the headline is printed as the first sentence of the first paragraph, so it counts toward that paragraph's 6 lines and should read as a sentence. The link ends the last paragraph. Spread across beats: markets, tech, world.

**latest** Headlines only, one line each, linked. 3 to 5 per category, in this key order: business (deals, Wall Street, Goldman; keep to 3), tech, world (world and US politics), pop_culture, sports. Sports: 49ers, Warriors and Giants news, big NFL and NBA headlines and trades, and major NFL injuries (a starter out for multiple games or the season, especially quarterbacks and anyone on the 49ers). The score card comes from data.json below the headlines; don't write scores as headlines. Each item: `{"title": "...", "url": "...", "source": "..."}`. Here `title` is your one-line headline (statement with a verb), not necessarily the article's. It prints in black; only the outlet name after it is the link.

**off_the_clock** 2 to 3 short items, rotating: ski conditions (November to April: Northeast and Tahoe), outdoors and backpacking, cars (Rivian etc.), AI tools, and food (a restaurant opening or review). NYC events belong in NYC today, not here. The topic goes at the start of the headline: "Ski report: Killington opens more terrain", "Cars: ...", "AI tools: ...". Body 1 to 3 sentences.

**emoji** (Top 3 and Off the clock only) One emoji about the story's subject, shown before its headline: ⛷️ for a ski report, 🚙 for a Rivian, 🏦 for a bank deal, 🛢️ for oil, 🗳️ for an election. Specific beats generic: pick the object or activity in the story, not a mood (no 🔥, 🚀, 📈 or faces). Never repeat one within the issue.
Strictly a real, standard emoji: exactly one, from the normal emoji keyboard. Never a symbol (✓ ★ ↗), a combined emoji (🧑‍💻, a skin tone, a flag) or anything drawn or made up. Prefer common emoji everyone recognizes over obscure ones. render.py rejects anything else.

**chart** (optional, on a Big read, Top 3, Holdings or Movers story) A chart is supporting evidence for the story, never decoration. Add one only when a picture of the numbers says something the words can't: a big data release (CPI, jobs, PCE), a Fed decision or rate expectations, a forward-looking event with a live prediction market (a shutdown, an election, a ruling), or a price move with a story behind its shape (the 10-year yield, oil). Most days have none or one; never more than 3 (code keeps the first 3 in placement order). Never force one.

You name the data; code fetches the exact numbers and draws it. Shape: `{"source": "...", "id": "...", "title": "...", "view": "odds" | "history", "transform": "level" | "yoy" | "mom", "period": "1m" | "3m" | "6m" | "1y" | "2y" | "5y", "unit": "%" (optional)}`.

- `kalshi` / `polymarket`: forward-looking odds. `id` is the Kalshi event ticker (`KXFEDDECISION-26DEC`) or the Polymarket event slug (`fed-decisions-dec-mar`). Find them with `python -m brief.charts --search "fed december"`. `view: "odds"` shows today's odds for each outcome as bars; `"history"` shows how the top outcomes moved over `period` (use `"1m"` or `"3m"`). Prefer Kalshi for US economics and the Fed; either for politics and events. Pick a market that is open and actually trading.
- `bls`: official US data, monthly. Common ids: CPI `CUUR0000SA0` and core CPI `CUUR0000SA0L1E` (`transform: "yoy"`), payrolls `CES0000000001` (`"mom"`: jobs added each month, in thousands), unemployment rate `LNS14000000` (`"level"`, `unit: "%"`), average hourly earnings `CES0500000003` (`"yoy"`), PPI final demand `WPSFD4` (`"yoy"`). Use `period: "2y"` for inflation.
- `yahoo`: a daily close. `^TNX` 10-year yield, `CL=F` oil, `GC=F` gold, `DX-Y.NYB` dollar index, or any stock ticker. `period` `"1m"` to `"1y"`.
- `title` is one plain line in sentence case that says what the chart shows, with no numbers: "Odds for the Fed's December decision", "Inflation, year over year", "Jobs added each month (thousands)".

After `python -m brief.charts` runs, read `run/charts.json` (its `alt` line has the chart's latest values) and look at each PNG in `run/charts/`. If a chart failed, looks wrong, or doesn't back up the story, delete its `chart` field. The chart's numbers count as known, so you may quote its latest value in the story ("inflation ran 3.7% over the past year") exactly as `alt` states it.

**memes** If `data.json` has meme candidates, look at each image (download it and view it) and pick up to 6. Fewer is fine; never pad with weak ones. What Wilson wants, in order: (1) banking, finance and markets; (2) tech and media; (3) popular memes about current events. Most finance and tech memes come from the newsletters (`community` "Short Squeez" or "Exec Sum"); prefer those, and use Lemmy candidates to fill. Skip anything offensive, NSFW, or purely partisan. Skip near-duplicates (the newsletters often post the same joke). Order them best first. List their exact `url` values from data.json. If you can't view images, pick newsletter memes first and say so in your final summary. If there are no candidates, an empty list; the section is skipped.

## Length

Whole issue 1,600 to 1,900 words (weekend about 1,000). Over budget, render.py trims the ends of The latest lists, then Off the clock. Better to cut it yourself.

## Editions

- **weekday** (Tue to Fri): everything.
- **monday**: same sections. Earnings shows "Reporting this week" from data; code handles YTD and the week previews.
- **weekend**: no movers, on_deck_today, holdings_news or earnings. "Markets" shows crypto only. Lighter (see Length).
- **holiday**: a weekday issue; code adds the closure line.

## Shape

```json
{
  "date": "2026-11-24",
  "edition": "weekday",
  "subject": "...",
  "intro": "...",
  "section_desc": {"your_day": "...", "before_the_bell": "...", "earnings": "...", "holdings": "...",
                   "big_read": "...", "top_3": "...", "latest": "...", "off_the_clock": "...", "memes": "..."},
  "your_day_nyc": [{"title": "...", "url": "https://...", "source": "Gothamist"}],
  "movers": [{"ticker": "NVDA", "body": "...", "link": {"title": "...", "url": "https://...", "source": "WSJ"}}],
  "on_deck_today": [{"time": "8:30", "text": "..."}],
  "holdings_news": [{"ticker": "PLTR", "headline": "PLTR: ...", "body": "...", "link": {...}}],
  "big_read": {"headline": "...", "body": "Para one.\n\nPara two.\n\nWhy it matters: ...", "link": {...}},
  "top_3": [{"emoji": "🏦", "headline": "...", "body": "...", "link": {...},
             "chart": {"source": "bls", "id": "CUUR0000SA0", "title": "Inflation, year over year", "transform": "yoy", "period": "2y"}},
            {...}, {...}],
  "latest": {"business": [...], "tech": [...], "world": [...], "pop_culture": [...], "sports": [...]},
  "off_the_clock": [{"emoji": "⛷️", "headline": "Ski report: ...", "body": "...", "link": {...}}],
  "memes": ["https://media.beehiiv.com/...", "https://lemmy.world/pictrs/image/..."]
}
```

The full schema is `brief/schema.py` (`Content`).
