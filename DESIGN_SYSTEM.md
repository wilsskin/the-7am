# The 7AM Design System

**Version:** 1.9
**Last Updated:** November 25, 2026
**Parent system:** [wms-portfolio DESIGN_SYSTEM.md](https://github.com/wilsskin/wms-portfolio/blob/main/DESIGN_SYSTEM.md) v3.0

Read this before making any visual change. The 7AM is a sibling of wilsonskinner.com: same tokens, same restraint. Where this file is silent, the portfolio's DESIGN_SYSTEM.md wins. If you're in a hurry, jump to [Quick Reference](#quick-reference) and [Do's and Don'ts](#dos-and-donts).

The reference issues are the visual source of truth. `build_reference.py` generates all three from these tokens:

| File | Edition |
|---|---|
| `templates/reference_issue.html` | Weekday (Tue–Fri). The main reference. |
| `templates/reference_monday.html` | Monday: YTD columns, "This week" calendar, earnings week, games this week |
| `templates/reference_weekend.html` | Sat/Sun: no equities, holdings or earnings |

A holiday issue is a weekday issue whose Before the bell description ends with the closure line. Icons live in `templates/icons/`. Build `templates/email.html.j2` by turning the helpers in `build_reference.py` into Jinja macros, not by designing from scratch.

### Changelog
- **1.9 (Nov 25, 2026):** section labels (h2) 22px (20px on phones). The latest's tag pills use tertiary text with an 18px SF Symbol inside (briefcase, apple.terminal, globe.americas, popcorn, sportscourt). Top 3 and Off the clock headlines start with one emoji chosen by Claude. "Around NYC" is now "NYC today" (up to 3). Before the bell shows 2–3 big movers instead of one standout. Market card adds the Dow; SOXX moves to holdings.
- **1.8 (Nov 25, 2026), Wilson's first-issue review:** masthead name and date share one vertical center line. All external links are Apple blue (`#007AFF`) at body size, no underline, ending in ↗; stories end with the article title as an inline link in the last paragraph ("Read on WSJ →" is gone); in The latest and Around NYC the headline is black text and only the outlet name is the link. Paragraphs max 6 lines on a phone (250 characters; render.py splits at a sentence break). The big read and Top 3 headlines are the first sentence of the first paragraph (Morning Brew style), still 500 and primary. Icons are SF Symbols in `#424245`, with Apple Weather's condition set. Weather row keeps the current temperature (primary) in the left column, then "H53° L41° – Cloudy until 4pm, then rain" with the high in Apple red and the low in Apple blue. Text colors move to apple.com's: primary `#1D1D1F`, a new tertiary `#424245` (icons), secondary `#6E6E73`.
- **1.7 (Nov 22, 2026):** Feedback section removed from the issue. Feedback still works by replying to the email (BUILD_PLAN.md §10b); nothing in the layout points to it.
- **1.6 (Nov 22, 2026):** feedback is now a reply to the email. The Feedback section is just its header (label + fixed description telling Wilson to reply); the button is gone, so the theme pill is used only for Wilson's birthday.
- **1.5 (Nov 22, 2026):** The latest's category labels (Business, Tech, World, Pop culture, Sports) are tag pills again; the sports card moves below the sports headlines; the Earnings description ends with who reports next on Tue–Fri.
- **1.4 (Nov 22, 2026):** Standout headline is just the ticker and move ("NVDA −6.40%"); Your day rows and On deck today rows are vertically centered; earnings cells are one line, "57.0B (+3.3%)", with the surprise in colored parentheses and no Beat/Miss word; "Reporting today" removed on weekdays; Monday "Reporting this week" is one row per day with company names only; Off the clock topic moves into the headline ("Ski report: ..."); tag pills are no longer used.
- **1.3 (Nov 22, 2026):** section labels back to the `heading` role: 20px, weight 500 (18px on phones). Weight 600 is no longer used. Sentence case and the one-line description stay.
- **1.2 (Nov 22, 2026), Wilson's second review:** section labels 16px, weight 600, sentence case, each followed by a one-line description; Your day main content in a card with icons (weather, subway, calendar); closure callout replaced by text in the Before the bell description; market and holdings tables headed "Asset"; holdings get a WTD/YTD column; Standout on one line with a longer write-up and link; tighter time column in On deck today; earnings cells show "Beat (+3.3%)" instead of the estimate line, and the per-company notes are gone; "Reported yesterday" and "Reporting today" use the small headline style; holdings stories have the ticker in the headline, with no cap on how many; all story headlines (including The big read) are 16px; Also Brewing renamed Top 3; sports moved to the end of The latest, with a score card (W/L on the left, Monday adds this week's games) and NFL injury headlines.
- **1.1 (Nov 22, 2026), Wilson's first review:** system font (SF Pro) instead of Inter; 96px between sections; read links gray like the portfolio's "View →"; body stays 16px on mobile; crypto joins the index card at the 4pm ET close; Earnings ahead of Holdings; "Around NYC" sub-label; Monday "This week" calendar; Off the Clock drops its cards; Feedback section; one card padding; red/green confirmed.

---

## Quick Reference

| What | Value |
|---|---|
| Font | System stack: SF Pro on Apple devices (see Text Styles) |
| Page background | `#F8F8F8` · `--color-bg` |
| Primary text | `#1D1D1F` · `--color-text-primary` |
| Tertiary (icons) | `#424245` · `--color-text-tertiary` |
| Secondary text | `#6E6E73` · `--color-text-secondary` |
| Card background | `#F0F0F0` · `--color-surface` |
| Lines inside cards | `#EBEBEB` · `--color-border-subtle` |
| Theme color | `#0079AF` · `--color-theme` |
| Links | `#007AFF` · `--color-link` (Apple systemBlue) |
| Issue title | `title` · 26px · 500 |
| Section label | 22px (20px phones) · 500 · sentence case · primary |
| Section description | `body` · 16px · 400 · secondary, 2px under the label |
| Story headline | small headline · 16px · 500 · primary |
| Body text | `body` · 16px · 400 · secondary (16px on mobile too) |
| Caption / meta / numbers | `meta` · 14px · 400 |
| Between sections | `--spacing-xxlarge` · 96px |
| Content width | 504px reading column (552px email incl. 24px side padding) |

---

## Visual Theme & Atmosphere

Editorial restraint, delivered to an inbox. The canvas is the same near-white `#F8F8F8` as the portfolio. Headlines and section labels are near-black `#1D1D1F`; body steps back to `#6E6E73`. Both are apple.com's text colors, with `#424245` between them for icons. Depth comes from spacing alone: no divider lines between sections, no shadows, no gradients, no illustrations.

Hierarchy is flat on purpose, like the portfolio: section labels are 20px and everything inside a section is 16px, told apart by weight (500 headline, 400 body), color (black vs gray) and 96px of space between sections.

Color enters the way it does on the case study pages: one theme color, used sparingly on the theme pill. Links are Apple blue with ↗, so anything that leaves the email looks the same everywhere. Green and red appear on market data and scores; Apple red and blue on the weather high and low. Everything else is black and gray.

The effect: a morning briefing that reads like a page from wilsonskinner.com. *The news speaks for itself.*

What we take from the newsletters Wilson reads:
- **Morning Brew:** numbers first in a compact table; one lead story with real paragraphs; scannable headline blocks; a light closer.
- **Exec Sum:** punchy subject line and intro; one-line headlines tagged with the outlet; memes to end.
- **NYT The Morning:** clear section labels so you always know where you are.
- **Axios:** one medium-weight lead-in ("Why it matters:") to mark a takeaway.

What we drop: ads, sponsor blocks, emoji section headers, stock photos, puns, GIFs, centered marketing layouts, divider lines.

**Name:** working name *The 7AM*, a nod to the portfolio hero caption "WORTH THE 3AM." Set in `config.yaml` (`brand.name`).

---

## Text Styles

Four roles, same as the portfolio. Do not invent sizes.

| Role | Name | Size (≤480px) | Weight | Line height | Letter-spacing | Color |
|---|---|---|---|---|---|---|
| Issue title | `title` | 26px (22px) | 500 | 30px (25px) | −0.02em | primary + secondary span |
| Headline | `heading` | 20px (18px) | 500 | 27px (24px) | −0.01em | primary |
| Body | `body` | 16px (16px) | 400 | 22px | 0 | secondary |
| Meta | `meta` | 14px | 400 | 19px | +0.01em | secondary |

`heading` (20px) is used for section labels, the masthead name and the temperature. Every story headline uses the small headline variant (16px), so a story never outranks its section.

**Font: the system font, not Inter.** Gmail (web, iOS and Android) does not load web fonts, so Inter would never show where Wilson reads the issue. The stack is:

```
-apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif
```

That gives SF Pro in Gmail on iPhone, Apple Mail and Chrome on a Mac. No `<link>` to Google Fonts.

**Weights:** 400 and 500 only. Never 600, 700 or `<strong>`/`<b>` defaults. "400 reads, 500 announces."

**Body stays 16px on phones.** The issue is mostly read on an iPhone, so the main reading size never shrinks. Only `title` and `heading` step down at ≤480px.

### Named variants (built from the four roles)

| Variant | Recipe | Use |
|---|---|---|
| Two-tone title | `title`, first sentence primary, the rest in a secondary `<span>` | The intro. Mirrors the portfolio hero h1. One per issue. |
| Section label | 22px/28px (20px/26px ≤480px), 500, −0.01em, sentence case, primary | Every section: "Your day", "Before the bell", "Top 3"... Same as the portfolio's `.subtitle-global` ("CarGurus finance calculator"). |
| Section description | `body`, secondary, 2px under the label | One line (two at most) under every section label, summarizing that section today. Written by Claude. |
| Small headline | `body` size, 500, primary | Every story headline (Big read, Top 3, Holdings, Off the clock), the standout line ("NVDA −6.40%"), "On deck today", "NYC today", "Reported yesterday", "Reporting this week". |
| Value text | `body`, primary | Calendar event titles, subway alert text, headline links in The latest. Same idea as `.caption-primary`. |
| Lead-in | `body`, 500, primary, inline | "Why it matters:" at the start of a paragraph. Max one per story. |
| Masthead date | monospace (SF Mono), 14px, +0.02em, uppercase, secondary | The one intentional style break, echoing the portfolio's hero caption. Nowhere else. |
| Numbers | `meta` + `font-variant-numeric: tabular-nums`, primary | Prices, percentages, EPS, times, scores. |

---

## Design Tokens

### Colors

| Token | Light | Dark (Apple Mail) | Use |
|---|---|---|---|
| `--color-bg` | `#F8F8F8` | `#0B0B0B` | Page background |
| `--color-text-primary` | `#1D1D1F` | `#F2F2F2` | Section labels, headlines, values, numbers |
| `--color-text-tertiary` | `#424245` | `#C7C7CC` | Icons (baked into the PNGs, so no dark swap) |
| `--color-text-secondary` | `#6E6E73` | `#9A9A9A` | Body, descriptions, sub-labels, meta |
| `--color-surface` | `#F0F0F0` | `#1A1A1A` | Cards, tag pills, meme placeholders |
| `--color-border-subtle` | `#EBEBEB` | `#2A2A2A` | Row lines inside cards only |
| `--color-theme` | `#0079AF` | `#4FB3E3` | Theme pill only (via its tint and line) |
| `--color-theme-tint` | `#D3E5ED` | `#0F2A38` | Theme pill fill (theme at 15% on bg) |
| `--color-theme-line` | `#7CB9D4` | `#1F5E7D` | Theme pill border (theme at 50% on bg) |
| `--color-up` | `#1B7A5E` | `#3DD6A8` | Positive moves and beats, W. JumboCode green (`#28A07E`) darkened to pass AA on cards. |
| `--color-down` | `#C03A3A` | `#FF6B6B` | Negative moves, Miss, L. Confirmed by Wilson Nov 22, 2026. |
| `--color-mta-45` | `#00933C` | same | 4/5 route bullets only |
| `--color-link` | `#007AFF` | `#0A84FF` | Every external link (Apple systemBlue), and the weather low |
| `--color-hi` | `#FF3B30` | `#FF453A` | Weather high only (Apple systemRed) |

Rules:
- The theme color is the CarGurus case study color (`#0079AF`), already part of the brand. Text at full strength, pills at 15% fill with a 50% border.
- Links are Apple blue, body size, no underline, followed by a non-breaking space and ↗ (`↗︎`, forced to text so iOS doesn't draw the emoji). One style for every external link. Apple blue is 3.9:1 on the page background: under AA for small text, accepted to match iOS.
- Up/down color is never the only signal: always a sign (+1.2% / −0.8%, an earnings surprise like (+3.3%)) or a letter (W / L). Use a real minus sign (−), not a hyphen.
- Hex values live in one Python dict (`brief/tokens.py`). Templates reference the dict, never raw hex.
- Never introduce a color outside this table. If one feels necessary, ask Wilson.

### Spacing

8px base, same tokens as the portfolio.

| Token | Value | Use in the email |
|---|---|---|
| `--spacing-unit` | 8px | Small headline to its list or card, small gaps |
| `--spacing-xsmall` | 16px | Section description to content, between paragraphs |
| `--spacing-small` | 24px | Between blocks inside a section |
| `--spacing-medium` | 32px | Between stories, masthead to title |
| `--spacing-xxlarge` | 96px | Between sections and above the footer (as `padding-top` on the incoming section). Same as the portfolio's gap between work cards. |
| side padding | 24px (16px ≤480px) | Left/right of the 504px column |

Label to description: 2px (the portfolio's `.text-container` gap). Paragraph to paragraph: 16px (the `.p-container` gap).

**Spacing rule:** space between sections is `padding-top` on the incoming section, never `padding-bottom` on the outgoing one.

### Radii

| Token | Value | Use |
|---|---|---|
| `--radius-sm` | 4px | Tag pills |
| `--radius-md` | 8px | Theme pill, memes, cards at ≤480px |
| `--radius-lg` | 16px | Cards |

### Depth

Two levels only. Email clients drop shadows unevenly, so there are none.

| Level | Treatment | Use |
|---|---|---|
| Flat | Nothing | Everything else, including all stories |
| Surface | `--color-surface` fill, `--radius-lg`, no border, padding 8px 16px | Tables: Your day card, market card, earnings card, holdings card, sports card |

**Text inside a card:** short labels and numbers only, plus value text. Gray on the card fill is 4.4:1, just under AA, so it is only for short labels like "Asset", "12:30" or "NFL". Stories never go in a card.

---

## Layout

- One centered table, `max-width: 552px` (504px reading column + 24px padding each side). This is the portfolio's reading column, so line lengths match the site.
- Single column always. No side-by-side layouts, so there's nothing to collapse on a phone.
- Mobile (≤480px) via one media query: side padding 16px, `title` 22px, `heading` 18px (section labels too), cards radius 8px. Everything else stays the same size.

---

## Components

**Preheader.** Hidden text after `<body>` that sets the inbox preview. First sentence of the intro, padded with `&zwnj;&nbsp;`.

**Masthead.** One row: "The 7AM" in `heading` (20px, 500, −0.01em, primary) on the left; masthead date on the right (mono, uppercase, "TUE NOV 24"). Both cells `valign="middle"` with a 27px line height, so they share one center line in every client. No logo image, no line under it.

**Title.** Two-tone `title`, 32px below the masthead. 2 to 5 sentences, aim for 3.

**Section header.** Section label, 2px, section description, then 16px to the content. 96px above. No line, no icon. Every section has a description.

**Story.** Small headline, 2px gap, body paragraphs with 16px between them. The last paragraph ends with the link inline. In The big read and Top 3 there is no separate headline: it is the first sentence of the first paragraph, in small-headline style (500, primary), with a period added, like Morning Brew.

**Paragraph.** `body`, at most 6 lines on a 390px phone: 250 characters including an inline headline and link (the mobile column holds ~43 characters a line). render.py splits longer paragraphs at a sentence break and warns when it can't.

**Link.** Apple blue, inherits the surrounding text size (16px), no underline, text then `&nbsp;↗`. In stories the text is the article's title; in headline rows it is the outlet name, kept on one line.

**Tag pill.** The portfolio's `.tag-pill`: `meta`, tertiary (`#424245`), `--color-surface` fill, 2px 6px 2px 4px padding, `--radius-sm`, with an 18px SF Symbol 4px before the text (`tag-business` briefcase, `tag-tech` apple.terminal, `tag-world` globe.americas, `tag-pop` popcorn, `tag-sports` sportscourt). Used only for the category labels in The latest, on their own line, 24px above (0 when first) and 10px below.

**Ticker in a card.** Inside a surface card a pill would vanish, so tickers are plain `meta` text at 500, primary.

**Theme pill.** The portfolio's `.impact-pill`: `meta`, primary text, `--color-theme-tint` fill, 1px `--color-theme-line` border, 6px 12px padding, `--radius-md`. Max one per section. Used only for Wilson's own birthday (Your day). Market closures are text in the Before the bell description, not a pill.

**Icon.** SF Symbols, regular weight, outline, in `#424245`, rendered to 60px PNGs (3x of 20px) with a transparent background by `templates/icons/make_icons.swift`. Set: `sun` (sun.max), `partly` (cloud.sun), `cloud`, `fog` (cloud.fog), `drizzle` (cloud.drizzle), `rain` (cloud.rain), `snow` (cloud.snow), `storm` (cloud.bolt.rain), picked from the WMO code the way Apple Weather does; `subway` (tram); `calendar`. PNG because Gmail strips SVG. `alt=""` because the text next to it carries the meaning. The dark gray is low-contrast on a dark-mode card.

**Your day card.** Surface card holding a three-column table: 32px icon column, 64px left column (route bullets, or a time, "All day" or day name in `meta` primary), then value text with an optional `meta` detail. The weather row has the current temperature in the left column (20px, 500, primary) and "H53° L41° – Cloudy until 4pm, then rain" as value text, with H in `--color-hi` and L in `--color-lo` at 500. The outlook comes from the hourly forecast: up to three spells of at least 2 hours. Every cell is vertically centered (`valign=\"middle\"`), so the icon, left value and text share one center line. 12px vertical padding per row, 1px `--color-border-subtle` line between rows. Order: weather (weather icon), subway (subway icon), today's calendar events and birthdays (calendar icon). Monday adds a "This week" `meta` header row inside the card, then one calendar row per event (day name left, time as `meta` detail after the title).

**Data card.** Surface card, 8px 16px padding (the only card padding). Header row in `meta` secondary, first column headed "Asset". Data rows in numbers style, 10px vertical padding, 1px `--color-border-subtle` line above each row. First column left-aligned, numbers right-aligned.

**Market card.** One data card for indices and crypto together: S&P 500, Dow, Nasdaq, Bitcoin, Ether. Columns: Asset, Price, 1D, WTD (Mondays YTD). Prices are from the 4pm ET close; crypto uses the same snapshot, not a 24-hour window.

**Holdings card.** Data card: Asset, Price, 1D, WTD (Mondays YTD).

**Earnings card.** Data card: Asset, Revenue, EPS, After hrs. Revenue and EPS cells are one line: the actual (primary), a space, then the surprise vs the estimate in parentheses colored up/down: "57.0B (+3.3%)", "179.5B (−0.3%)". No Beat/Miss word, no notes.

**Big movers.** 2–3 per day, 24px apart. Each is one small headline line, just the ticker and its move: "NVDA −6.40%" with the move in up/down, then one paragraph on why ending in the link. No label.

**Move.** Numbers style with sign, colored up/down; `0.00%` in secondary.

**Meta row.** Two columns: left (a time or a day name in `meta`), right a value text, optionally followed by a `meta` detail. 48px left column, 12px between rows. Both cells vertically centered (`valign="middle"`) so the 14px time sits on the same center line as the 16px text.

**Headline row.** Value text (primary, 400, not a link), then the outlet as a link ("Gothamist ↗") on the same line. 12px between rows. No bullets.

**Sub-heading.** "🏙️ NYC today" (the one fixed emoji, written by code) uses the small headline (`<h3>`, 16px, 500, primary), like "On deck today": 24px above (0 when first), 8px below.

**Route bullet.** 20px circle, `--color-mta-45`, white 12px 500 number. The only place a non-system color appears, because the color is the information.

**Sports card.** Surface card with a three-column table: 40px left column (W or L in up/down at 500, or a day name), the score or matchup in numbers style primary ("49ers 27, Packers 20"), and the league or start time right-aligned in `meta` secondary. Monday adds a "This week" header row and the 49ers and Warriors games for the week. No results and not Monday → no card.

**Meme.** Full width (max 504px), `--radius-md`, 16px apart, explicit `width`, `alt="Meme"`, `display:block`.

**Footer.** 96px above. "© 2026 Wilson Skinner" in `body` secondary (same as the portfolio footer), then a `meta` line: "Generated 6:41am ET. All sections delivered." or the list of unavailable sections.

**Unavailable state.** Keep the section label; the description becomes "Market data unavailable this morning." Never hide the label.

---

## Section Layouts

Fixed order. Day variants are in BUILD_PLAN.md §5 and in the three reference files. Every section starts with a section header (label + description).

| # | Section | Layout |
|---|---|---|
| — | Subject line | ≤60 chars, sentence case, no emoji, no prefix. "Nvidia beat, and it still wasn't enough." |
| 1 | Masthead + Title | Masthead row, then two-tone title. No section label. |
| 2 | Your day | Your day card (weather, subway, calendar, birthdays; Monday adds "This week") → "NYC today" small headline + up to 3 headline rows. Skip any empty row or part. Never write "No events today." |
| 3 | Before the bell | Description ends with the closure line when the market is closed or closes early this week → market card → 2–3 big movers (24px) → "On deck today" small headline + meta rows (24px). Weekend: label "Markets", Bitcoin and Ether only. |
| 4 | Earnings | Description on Tue–Fri ends with who reports the next trading day (Friday: Monday), added by code. → "Reported yesterday" small headline + earnings card. No "Reporting today". Monday: "Reporting this week" small headline + one meta row per day (day name left, company names right, comma-separated, no tickers or timing) instead. Empty → skip the section. Not on weekends. |
| 5 | Your holdings | Holdings card. Then a story for every holding with relevant, recent news (no cap), headline starting with the ticker: "PLTR: Army expands its software contract". 32px between stories. No news → card only. Not on weekends. |
| 6 | The big read | Small headline, 3–4 body paragraphs, optional one lead-in, read link. No image. |
| 7 | Top 3 | Three stories, 32px apart: emoji + headline as the first sentence, 2 paragraphs, link inline at the end. |
| 8 | The latest | Tag pill categories Business, Tech, World, Pop culture, then Sports last; 3–5 headline rows each. Sports: headline rows → 16px → sports card (if any results, or Monday). |
| 9 | Off the clock | 2–3 stories, 32px apart: small headline starting with an emoji, then the topic ("Ski report: Killington opens more terrain"), body, read link. No cards, no eyebrow. |
| 10 | Meme roundup | Up to 6 memes stacked (Wilson, Nov 26, 2026). No captions. |
| — | Footer | As above. |

---

## Email Engineering Rules

Email clients are not browsers. These are non-negotiable.

- Table layout (`role="presentation"`). No flexbox, grid or `position`.
- Inline styles on every element. Build them from `brief/tokens.py` inside Jinja macros, so there is no CSS-inlining step and no extra dependency. The `<style>` block holds only the ≤480px query and the dark mode query.
- Dark mode: `<meta name="color-scheme" content="light dark">` plus `@media (prefers-color-scheme: dark)` swapping colors via the classes in the reference file (`.bg`, `.card`, `.c-primary`, `.c-secondary`, `.c-theme`, `.c-up`, `.c-down`, `.b-subtle`, `.pill`, `.tpill`). Apple Mail follows it; Gmail apps invert on their own. Never put text in images.
- No web fonts. System font stack only (see Text Styles).
- Icons are PNG attachments embedded inline (`src="cid:calendar"`), not hosted, so there's nothing to host and they show even before "load images". The mockup uses `icons/calendar.png` instead.
- Total HTML under 100KB, or Gmail clips the email. render.py fails loudly above 95KB.
- Images: memes hotlinked over https; icons inline. The email must read completely with images off.
- Links: absolute https, no tracking parameters.
- Plain-text version generated from the same content.json.
- Test before calling it done: Gmail iOS (light and dark), Gmail web, Apple Mail iOS (light and dark). Screenshot at 390px and 640px with Playwright and compare against the reference for that edition.

---

## Do's and Don'ts

### Do
- Use the four text roles and the named variants. Nothing else.
- Keep body text secondary (#6E6E73); reserve primary for section labels, headlines, values and numbers.
- Give every section a one-line description.
- Use spacing to separate sections. 96px, always as padding-top.
- Use the theme color only on the theme pill.
- Make every number tabular and every move signed.
- Use the one link style (Apple blue, ↗) for every external link.
- Keep every paragraph to 6 phone lines.
- Keep the masthead date as the only monospace text.
- Keep body at 16px on every screen size.

### Don't
- Don't use weights 600 or 700, or default `<strong>`/`<b>` styling.
- Don't write section labels in all caps.
- Don't add divider lines between sections. Lines exist only inside cards.
- Don't add shadows, gradients, emoji section headers or stock images.
- Don't introduce colors outside the token table.
- Don't use arbitrary spacing. Round to the nearest token.
- Don't use em dashes or exclamation points in the issue (birthday line excepted).
- Don't put more than one theme pill in a section, and don't use one for market closures.
- Don't load web fonts or use SVG.
- Don't put a story in a card. Cards are for tables.

---

## Accessibility

| Text | Contrast | Passes |
|---|---|---|
| `#1D1D1F` on `#F8F8F8` | 15.9:1 | AAA |
| `#424245` on `#F8F8F8` | 9.4:1 | AAA |
| `#6E6E73` on `#F8F8F8` | 4.78:1 | AA |
| `#6E6E73` on `#F0F0F0` | 4.45:1 | Just under AA. Short labels inside cards only, never sentences |
| `#0079AF` on `#F8F8F8` | 4.5:1 | AA |
| `#007AFF` on `#F8F8F8` | 3.9:1 | AA large only. Accepted to match iOS |
| `#FF3B30` on `#F0F0F0` | 3.2:1 | AA large only. Weather high, always with the "H" |
| `#1B7A5E` on `#F0F0F0` | 4.6:1 | AA |
| `#C03A3A` on `#F0F0F0` | 4.7:1 | AA |

- `lang="en"`, a real `<title>`, `role="presentation"` on layout tables.
- One `<h1>` (the title), `<h2>` section labels, `<h3>` story headlines.
- Meme `alt="Meme"`. Icons `alt=""` (decorative). Route bullets have the line number as text, not an image.
- Color is never the only signal (signs, W/L).

---

## Agent Prompt Guide

### Quick color reference
```
Page background:  #F8F8F8   Primary text:  #1D1D1F   Secondary text: #6E6E73   Tertiary: #424245
Card surface:     #F0F0F0   Card lines:    #EBEBEB   Theme:          #0079AF
Up:               #1B7A5E   Down:          #C03A3A   Link:           #007AFF
```

### Example component prompts

**Title:**
> `<h1>`, system font 26px weight 500, line-height 30px, letter-spacing −0.02em. First sentence #1D1D1F, remaining sentences in a `<span>` at #6E6E73. 22px at ≤480px.

**Section header:**
> `<h2>`, system font 20px weight 500, line-height 27px, letter-spacing −0.01em, sentence case, #1D1D1F. 18px at ≤480px. Then `<p>` 16px 400 #6E6E73, 2px above. 96px padding-top on the header, 16px below the description. No line.

**Story:**
> `<h3>` 16px weight 500, #1D1D1F. 2px gap. Body `<p>` 16px 400, line-height 22px, #6E6E73, 16px between paragraphs, max 250 characters each. The last paragraph ends with the article title as a link: #007AFF, no underline, "Title&nbsp;↗".

**Data card:**
> Table, background #F0F0F0, radius 16px (8px ≤480px), padding 8px 16px. Header cells 14px #6E6E73, first one "Asset". Rows 14px tabular-nums #1D1D1F, 10px vertical padding, 1px #EBEBEB top border. Moves signed and colored #1B7A5E / #C03A3A.

**Theme pill:**
> Single-cell table, background #D3E5ED, 1px border #7CB9D4, radius 8px, padding 6px 12px, 14px #1D1D1F.

### Iteration guide
- Reach for a role or variant before writing any font rule.
- Two weights: 400 reads, 500 announces.
- Secondary is the default for body; primary is for labels, headlines, values and numbers.
- If a value isn't a token, round to the nearest token.
- When in doubt, open the portfolio's DESIGN_SYSTEM.md and do what it does.
