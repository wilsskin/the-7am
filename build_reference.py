"""Generates the reference issues from the DESIGN_SYSTEM.md tokens. Sample content only.

Run: python build_reference.py
Writes three files, one per edition:
  templates/reference_issue.html    weekday (Tue to Fri), the main visual source of truth
  templates/reference_monday.html   Monday: YTD column, week calendar, week earnings, games this week
  templates/reference_weekend.html  Saturday/Sunday: no equities, holdings or earnings
A holiday is a weekday issue whose Before the Bell description ends with the closure line.

Icons are PNGs in templates/icons/ (60px, drawn at 3x, shown at 20px). The mockup links
them by relative path; the real email embeds them inline (cid:), see BUILD_PLAN.md §9.

The helper functions below are the components in DESIGN_SYSTEM.md. Port them into Jinja
macros for email.html.j2.
"""
import os

# System font stack: SF Pro on Apple devices (Gmail iOS, Apple Mail, Chrome on Mac),
# Segoe UI on Windows, Roboto on Android. Gmail does not load web fonts like Inter.
SANS = "-apple-system,BlinkMacSystemFont,'SF Pro Text',system-ui,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,'SF Mono',Menlo,Consolas,monospace"
T = dict(bg="#F8F8F8", primary="#000000", secondary="#6F6F6F",
         surface="#F0F0F0", subtle="#EBEBEB", theme="#0079AF", theme_tint="#D3E5ED",
         theme_line="#7CB9D4", up="#1B7A5E", down="#C03A3A")
SECTION_GAP = 96   # padding-top on every incoming section and on the footer
NUM = f"font-family:{SANS};font-size:14px;line-height:19px;letter-spacing:0.01em;font-variant-numeric:tabular-nums;"
ICON_SRC = "icons/{}.png"   # email.html.j2 uses "cid:{}" instead


# ---------- components ----------

def h1(lead, rest):
    return (f'<tr><td class="px" style="padding:32px 24px 0 24px;">'
            f'<h1 class="t-title" style="margin:0;font-family:{SANS};font-size:26px;line-height:30px;font-weight:500;letter-spacing:-0.02em;color:{T["primary"]};">'
            f'<span class="c-primary">{lead}</span> <span class="c-secondary" style="color:{T["secondary"]};">{rest}</span></h1></td></tr>')

def label(text, desc, top=SECTION_GAP):
    # Section label: heading role (20px, 500), sentence case, primary. Then a one-line description in body secondary.
    return (f'<tr><td class="px sec" style="padding:{top}px 24px 16px 24px;">'
            f'<h2 class="c-primary t-heading" style="margin:0;font-family:{SANS};font-size:20px;line-height:27px;font-weight:500;letter-spacing:-0.01em;color:{T["primary"]};">{text}</h2>'
            f'<p class="c-secondary" style="margin:0;padding-top:2px;font-family:{SANS};font-size:16px;line-height:22px;font-weight:400;color:{T["secondary"]};">{desc}</p>'
            f'</td></tr>')

def row(inner, top=0):
    return f'<tr><td class="px" style="padding:{top}px 24px 0 24px;">{inner}</td></tr>'

def subtitle(text, top=0):
    # Small headline: every story headline, the standout line, "On deck today", "Reported yesterday".
    return f'<h3 class="c-primary" style="margin:0;padding-top:{top}px;font-family:{SANS};font-size:16px;line-height:22px;font-weight:500;letter-spacing:0;color:{T["primary"]};">{text}</h3>'

def para(text, top=2):
    return f'<p class="c-secondary" style="margin:0;padding-top:{top}px;font-family:{SANS};font-size:16px;line-height:22px;font-weight:400;color:{T["secondary"]};">{text}</p>'

def readlink(outlet, url, top=8):
    # Same as the portfolio's "View →": meta size, secondary, no underline.
    return (f'<p style="margin:0;padding-top:{top}px;font-family:{SANS};font-size:14px;line-height:19px;letter-spacing:0.01em;">'
            f'<a href="{url}" class="c-secondary" style="color:{T["secondary"]};text-decoration:none;">Read on {outlet} →</a></p>')

def caption(text, color="secondary"):
    return f'<span class="c-{color}" style="font-family:{SANS};font-size:14px;line-height:19px;letter-spacing:0.01em;color:{T[color]};">{text}</span>'

def tk(text):  # ticker inside a card: plain text, medium
    return f'<span style="font-weight:500;">{text}</span>'

def pill(text):  # tag-pill (the portfolio's .tag-pill)
    return (f'<span class="pill" style="font-family:{SANS};font-size:14px;line-height:19px;letter-spacing:0.01em;font-weight:400;'
            f'color:{T["secondary"]};background-color:{T["surface"]};border-radius:4px;padding:2px 4px;">{text}</span>')

def badge_label(text, top=24):  # category label in The latest: a tag pill on its own line
    return f'<p style="margin:0;padding:{top}px 0 10px 0;line-height:19px;">{pill(text)}</p>'

def theme_pill(text, href=None):  # impact-pill; used for Wilson's own birthday
    inner = text if not href else f'<a href="{href}" class="c-primary" style="color:{T["primary"]};text-decoration:none;">{text}</a>'
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr><td class="tpill" style="padding:6px 12px;border-radius:8px;'
            f'background-color:{T["theme_tint"]};border:1px solid {T["theme_line"]};font-family:{SANS};font-size:14px;line-height:19px;letter-spacing:0.01em;color:{T["primary"]};">{inner}</td></tr></table>')

def move(v):
    c = "up" if v.startswith("+") else ("down" if v.startswith("−") else "secondary")
    return f'<span class="c-{c}" style="color:{T[c]};">{v}</span>'

def card(inner):
    # One padding for every card: 16px left/right, so all card text shares one inset.
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="card" style="background-color:{T["surface"]};border-radius:16px;">'
            f'<tr><td style="padding:8px 16px;">{inner}</td></tr></table>')

def table(header, rows):
    h = "".join(f'<td align="{"left" if i==0 else "right"}" class="c-secondary" style="padding:10px 0 8px 0;{NUM}color:{T["secondary"]};">{c}</td>' for i, c in enumerate(header))
    out = f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>{h}</tr>'
    for r in rows:
        cells = ""
        for i, c in enumerate(r):
            align = "left" if i == 0 else "right"
            cells += f'<td align="{align}" valign="top" class="c-primary b-subtle" style="padding:10px 0;border-top:1px solid {T["subtle"]};{NUM}color:{T["primary"]};">{c}</td>'
        out += f"<tr>{cells}</tr>"
    return out + "</table>"

def meta_rows(items, left_w=72, valign="top"):
    # valign="middle" centers the 14px left cell on the 16px value text beside it.
    out = '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'
    for i, (left, right) in enumerate(items):
        pb = "0" if i == len(items) - 1 else "12px"
        out += (f'<tr><td width="{left_w}" valign="{valign}" style="width:{left_w}px;padding-bottom:{pb};">{left}</td>'
                f'<td valign="{valign}" style="padding-bottom:{pb};">{right}</td></tr>')
    return out + "</table>"

def body16(text, color="primary"):
    return f'<span class="c-{color}" style="font-family:{SANS};font-size:16px;line-height:22px;color:{T[color]};">{text}</span>'

def headline_rows(items):
    out = ""
    for i, (h, src, url) in enumerate(items):
        pb = 0 if i == len(items) - 1 else 12
        out += (f'<p style="margin:0;padding-bottom:{pb}px;font-family:{SANS};font-size:16px;line-height:22px;">'
                f'<a href="{url}" class="c-primary" style="color:{T["primary"]};text-decoration:none;">{h}</a> '
                f'{caption(src)}</p>')
    return out

def sublabel(text, top=24):
    return f'<p class="c-secondary" style="margin:0;padding:{top}px 0 8px 0;font-family:{SANS};font-size:14px;line-height:19px;letter-spacing:0.01em;color:{T["secondary"]};">{text}</p>'

def gap(px):
    return f'<div style="height:{px}px;line-height:{px}px;font-size:1px;">&nbsp;</div>'

def icon(name):
    return f'<img src="{ICON_SRC.format(name)}" width="20" height="20" alt="" style="display:block;width:20px;height:20px;border:0;">'

def route_bullets(lines):
    cells = []
    for n in lines:
        cells.append(f'<td align="center" width="20" style="width:20px;height:20px;border-radius:10px;background-color:#00933C;color:#FFFFFF;font-family:{SANS};font-size:12px;line-height:20px;font-weight:500;">{n}</td>')
    return ('<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
            + '<td width="4" style="width:4px;"></td>'.join(cells) + '</tr></table>')

def icon_table(rows):
    """Your Day card body. Each row: (icon name, left cell, right cell), or ("header", text).
    Three columns: 32px icon, 64px left (temperature, route bullets, time, day), value text."""
    out = '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'
    first = True
    for r in rows:
        if r[0] == "header":
            out += (f'<tr><td colspan="3" class="c-secondary" style="padding:16px 0 4px 0;{NUM}color:{T["secondary"]};">{r[1]}</td></tr>')
            first = True
            continue
        name, left, right = r
        line = "" if first else f"border-top:1px solid {T['subtle']};"
        cls = "" if first else ' class="b-subtle"'
        # Every cell vertically centered, so icon, left value and text share one center line.
        out += (f'<tr><td width="32" valign="middle"{cls} style="width:32px;padding:12px 0;{line}">{icon(name)}</td>'
                f'<td width="64" valign="middle"{cls} style="width:64px;padding:12px 0;{line}">{left}</td>'
                f'<td valign="middle"{cls} style="padding:12px 0;{line}">{right}</td></tr>')
        first = False
    return out + "</table>"

def er(act, pct):
    # Earnings cell, one line: actual, then the surprise vs estimate in colored parentheses.
    c = "up" if pct.startswith("+") else ("down" if pct.startswith("−") else "secondary")
    return f'{act} <span class="c-{c}" style="color:{T[c]};">({pct})</span>'

def wl(result):
    c = "up" if result == "W" else "down"
    return f'<span class="c-{c}" style="color:{T[c]};font-weight:500;">{result}</span>'


# ---------- sections ----------

NYC = [("Congestion pricing revenue tops projections for the third straight month", "NYT", "https://www.nytimes.com/"),
       ("Rockefeller Center tree lighting set for December 2", "Gothamist", "https://gothamist.com/")]

def your_day(edition, desc):
    P = [label("Your day", desc)]
    rows = [("cloud", f'<span class="c-theme" style="font-family:{SANS};font-size:20px;line-height:22px;font-weight:500;letter-spacing:-0.01em;color:{T["theme"]};">48°</span>',
             body16("Cloudy, high 53°, low 41°.") + "<br>" + body16("Rain likely after 4pm.", "secondary"))]
    if edition != "weekend":
        rows.append(("subway", route_bullets(["4", "5"]), body16("Delays in both directions after a signal problem at Grand Central.")))
        rows.append(("calendar", caption("12:30", "primary"), body16("Team lunch") + " " + caption("200 West St")))
    rows.append(("calendar", caption("All day", "primary"), body16("Sample Friend's birthday 🎂")))
    if edition == "monday":
        rows.append(("header", "This week"))
        rows += [("calendar", caption("Tue", "primary"), body16("Design review") + " " + caption("10:00")),
                 ("calendar", caption("Wed", "primary"), body16("Flight to SFO") + " " + caption("6:15pm")),
                 ("calendar", caption("Thu", "primary"), body16("Thanksgiving") + " " + caption("All day"))]
    P.append(row(card(icon_table(rows))))
    P.append(row(sublabel("Around NYC") + headline_rows(NYC)))
    return P

def market_card(edition):
    if edition == "weekend":
        return card(table(["Asset", "Price", "1D", "WTD"], [
            ["Bitcoin", "97,420", move("+1.84%"), move("+3.10%")],
            ["Ether", "3,512", move("0.00%"), move("−1.25%")],
        ]))
    mon = edition == "monday"
    return card(table(["Asset", "Price", "1D", "YTD" if mon else "WTD"], [
        ["S&amp;P 500", "6,812.40", move("−0.62%"), move("+14.80%" if mon else "−0.62%")],
        ["Nasdaq", "23,104.77", move("−1.08%"), move("+19.42%" if mon else "−1.08%")],
        ["SOXX", "284.15", move("−2.31%"), move("+22.06%" if mon else "−2.31%")],
        ["Bitcoin", "97,420", move("+1.84%"), move("+4.95%" if mon else "+1.84%")],
        ["Ether", "3,512", move("0.00%"), move("−6.30%" if mon else "0.00%")],
    ]))

def before_the_bell(edition, desc):
    if edition == "weekend":
        return [label("Markets", desc), row(market_card(edition))]
    P = [label("Before the bell", desc)]
    P.append(row(market_card(edition)))
    # Standout: just the ticker and its move as the headline.
    P.append(row(subtitle(f'NVDA <span style="{NUM}font-size:16px;">{move("−6.40%")}</span>') +
                 para("Record quarter on every line, but data center guidance came in under what investors were hoping for. "
                      "It was the biggest one-day drop among $100B+ companies and pulled the rest of the chip sector down with it.") +
                 readlink("WSJ", "https://www.wsj.com/"), top=24))
    P.append(row(subtitle("On deck today") + gap(8) + meta_rows([
        (caption("8:30"), body16("Chicago Fed national activity index")),
        (caption("2:00"), body16("Fed governor speaks on bank capital rules")),
    ], left_w=48, valign="middle"), top=24))
    return P

def earnings(edition, desc):
    # Own section, right after Before the Bell. Skipped entirely when empty.
    P = [label("Earnings", desc)]
    if edition == "monday":
        # One row per day, company names only.
        P.append(row(subtitle("Reporting this week") + gap(8) + meta_rows([
            (caption("Mon"), body16("Zoom Communications")),
            (caption("Tue"), body16("Dell Technologies, Salesforce")),
            (caption("Wed"), body16("Deere")),
        ], left_w=48, valign="middle")))
        return P
    earn = table(["Asset", "Revenue", "EPS", "After hrs"], [
        [tk("NVDA"), er("57.0B", "+3.3%"), er("1.30", "+4.0%"), move("−6.40%")],
        [tk("WMT"), er("179.5B", "−0.3%"), er("0.62", "+3.3%"), move("+2.10%")],
    ])
    P.append(row(subtitle("Reported yesterday") + gap(8) + card(earn)))
    return P

def holdings(edition, desc):
    P = [label("Your holdings", desc)]
    mon = edition == "monday"
    P.append(row(card(table(["Asset", "Price", "1D", "YTD" if mon else "WTD"], [
        [tk("GOOGL"), "312.48", move("+0.92%"), move("+38.20%" if mon else "+0.92%")],
        [tk("PLTR"), "186.10", move("−3.17%"), move("+141.05%" if mon else "−3.17%")],
        [tk("GEV"), "642.05", move("+1.40%"), move("+92.64%" if mon else "+1.40%")],
        [tk("COST"), "958.30", move("+0.15%"), move("+4.71%" if mon else "+0.15%")],
        [tk("V"), "348.72", move("−0.44%"), move("+10.33%" if mon else "−0.44%")],
        [tk("GS"), "812.66", move("+0.58%"), move("+41.90%" if mon else "+0.58%")],
    ]))))
    # One story per holding with real news. No cap: a big day can have several.
    stories = [("PLTR: Army expands its software contract", "Placeholder. Two to three sentences on what happened and why it matters to the position. Any number comes from data.json, never from the article.", "WSJ", "https://www.wsj.com/"),
               ("GOOGL: Gemini update ships to Workspace customers", "Placeholder. A second holding with news. Every holding with relevant, recent news gets a story, as many as the day calls for.", "NYT", "https://www.nytimes.com/")]
    for i, (hd, b, o, u) in enumerate(stories):
        P.append(row(subtitle(hd) + para(b) + readlink(o, u), top=24 if i == 0 else 32))
    return P

def big_read(desc):
    return [label("The big read", desc), row(
        subtitle("Sample headline: the AI trade hits its first real test") +
        para("Placeholder paragraph one. About 300 words across three or four short paragraphs, in the Morning Brew shape: what happened, the context, why it matters, what to watch.") +
        para("Placeholder paragraph two. Short declarative sentences. Strong verbs. Numbers over adjectives. No jokes, no em dashes, no filler.", 16) +
        para('<span class="c-primary" style="color:#000000;font-weight:500;">Why it matters:</span> Placeholder paragraph three. One medium-weight lead-in in black marks the takeaway.', 16) +
        readlink("NYT", "https://www.nytimes.com/", 16))]

def top_3(desc):
    P = [label("Top 3", desc)]
    stories = [("Sample story one headline with a verb", "Placeholder. About 100 words: the news first, then context, then why it matters.", "Reuters", "https://www.reuters.com/"),
               ("Sample story two headline with a verb", "Placeholder. Same shape, different beat: markets, tech, world.", "WSJ", "https://www.wsj.com/"),
               ("Sample story three headline with a verb", "Placeholder. If it needs more than 120 words, it belongs in The Big Read.", "BBC", "https://www.bbc.com/")]
    for i, (hd, b, o, u) in enumerate(stories):
        P.append(row(subtitle(hd) + para(b) + readlink(o, u), top=0 if i == 0 else 32))
    return P

def sports_card(edition):
    """W/L (or day) in the left column. Results from last night (Monday: the weekend).
    Monday also lists this week's 49ers/Warriors games. Returns "" when there's nothing."""
    rows = [(wl("W"), "49ers 27, Packers 20", "NFL"), (wl("L"), "Warriors 108, Lakers 115", "NBA")]
    out = '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'
    def r(left, mid, right, first=False):
        line = "" if first else f"border-top:1px solid {T['subtle']};"
        cls = "" if first else ' class="b-subtle"'
        return (f'<tr><td width="40" valign="top"{cls} style="width:40px;padding:10px 0;{line}{NUM}color:{T["primary"]};">{left}</td>'
                f'<td valign="top"{cls} style="padding:10px 0;{line}{NUM}color:{T["primary"]};" class="c-primary">{mid}</td>'
                f'<td align="right" valign="top"{cls} style="padding:10px 0;{line}{NUM}color:{T["secondary"]};" class="c-secondary">{right}</td></tr>')
    for i, x in enumerate(rows):
        out += r(*x, first=(i == 0))
    if edition == "monday":
        out += f'<tr><td colspan="3" class="c-secondary" style="padding:16px 0 4px 0;{NUM}color:{T["secondary"]};">This week</td></tr>'
        out += r(caption("Wed", "primary"), "Warriors vs Rockets", "7:30pm", first=True)
        out += r(caption("Thu", "primary"), "49ers vs Seahawks", "8:20pm")
    return card(out + "</table>")

def latest(edition, desc):
    groups = [
        ("Business", [("Sample headline about a deal or Wall Street move", "WSJ", "https://www.wsj.com/"),
                      ("Sample headline: Goldman news kept to one line", "CNBC", "https://www.cnbc.com/"),
                      ("Sample headline about the Fed", "Reuters", "https://www.reuters.com/")]),
        ("Tech", [("Sample headline about a model launch", "The Verge", "https://www.theverge.com/"),
                  ("Sample headline about big tech regulation", "NYT", "https://www.nytimes.com/")]),
        ("World", [("Sample world headline", "AP", "https://apnews.com/"),
                   ("Sample politics headline", "BBC", "https://www.bbc.com/")]),
        ("Pop culture", [("Sample box office headline", "Variety", "https://variety.com/"),
                         ("Sample music or streaming headline", "NYT", "https://www.nytimes.com/")]),
    ]
    html = ""
    for i, (cat, items) in enumerate(groups):
        html += badge_label(cat, 0 if i == 0 else 24) + headline_rows(items)
    # Sports last: headlines, then the score card (only if there are results, or it's Monday).
    html += badge_label("Sports") + headline_rows([
        ("Sample headline: star quarterback out for the season with a torn ACL", "ESPN", "https://www.espn.com/"),
        ("Sample headline about a big NFL trade", "ESPN", "https://www.espn.com/"),
        ("Sample Giants offseason headline", "The Athletic", "https://www.nytimes.com/athletic/")]) + gap(16) + sports_card(edition)
    return [label("The latest", desc), row(html)]

def off_the_clock(desc):
    P = [label("Off the clock", desc)]
    # Topic goes in the headline: "Ski report: ...". No eyebrow.
    items = [("Ski report", "Killington opens more terrain this weekend", "Placeholder. Base depth, lifts open, snow in the forecast.", "Killington", "https://www.killington.com/"),
             ("Things to do", "a market or show worth the trip", "Placeholder. Where, when, why it's worth it. Never the same item as Around NYC.", "Time Out", "https://www.timeout.com/newyork")]
    for i, (lab, t, b, o, u) in enumerate(items):
        P.append(row(subtitle(f"{lab}: {t}") + para(b) + readlink(o, u), top=0 if i == 0 else 32))
    return P

def memes(desc):
    P = [label("Meme roundup", desc)]
    for i, h in enumerate([300, 240]):
        P.append(row(f'<div class="meme-ph" style="height:{h}px;line-height:{h}px;border-radius:8px;background-color:{T["surface"]};text-align:center;font-family:{SANS};font-size:14px;color:{T["secondary"]};">Meme {i+1}</div>', top=0 if i == 0 else 16))
    return P

def footer():
    return [f'''<tr><td class="px" style="padding:{SECTION_GAP}px 24px 0 24px;">
<p class="c-secondary" style="margin:0;font-family:{SANS};font-size:16px;line-height:22px;color:{T["secondary"]};">© 2026 Wilson Skinner</p>
<p class="c-secondary" style="margin:0;padding-top:4px;font-family:{SANS};font-size:14px;line-height:19px;letter-spacing:0.01em;color:{T["secondary"]};">Generated 6:41am ET. All sections delivered. Sample content.</p>
</td></tr>''']


# ---------- editions ----------
# desc: one-line section descriptions, written by Claude each morning (content.json
# `section_desc`). The closure line at the end of Before the Bell is added by code.

CLOSURE = "Markets close Thursday for Thanksgiving, early close Friday at 1pm."

EDITIONS = {
    "weekday": dict(file="reference_issue.html", date="Tue Nov 24",
                    lead="Nvidia beat on every line and the stock still fell.",
                    rest="Chips dragged the Nasdaq lower and took the S&amp;P with it. Markets close Thursday for Thanksgiving, so expect a thin week.",
                    desc=dict(day="Cloudy with rain after 4pm, 4/5 delays, lunch at 12:30.",
                              bell="Chips led a down day for the Nasdaq. " + CLOSURE,
                              # Tue–Fri: render.py appends who reports next ("Deere reports tomorrow.").
                              earnings="Nvidia beat on both lines and still fell after hours. Walmart missed on revenue. Deere reports tomorrow.",
                              holdings="A mixed day. PLTR and GOOGL both had news.",
                              big="Why Nvidia's beat wasn't enough for the AI trade.",
                              top3="A Fed nominee, a chip export rule and a big bank deal.",
                              latest="Quick hits across business, tech, world, culture and sports.",
                              clock="Early ski terrain and one thing worth doing this week.",
                              memes="Four from today's feeds.")),
    "monday": dict(file="reference_monday.html", date="Mon Nov 23",
                   lead="Nvidia beat on every line and the stock still fell.",
                   rest="Chips dragged the Nasdaq into Friday's close. Thanksgiving week starts quiet, with markets shut Thursday.",
                   desc=dict(day="Cloudy with rain after 4pm and a short week ahead.",
                             bell="Chips closed last week on a down note. " + CLOSURE,
                             earnings="A light holiday week. Zoom tonight, then Dell and Salesforce Tuesday.",
                             holdings="PLTR leads the year. PLTR and GOOGL both had news this weekend.",
                             big="Why Nvidia's beat wasn't enough for the AI trade.",
                             top3="A Fed nominee, a chip export rule and a big bank deal.",
                             latest="Quick hits across business, tech, world, culture and sports.",
                             clock="Early ski terrain and one thing worth doing this week.",
                             memes="Four from the weekend's feeds.")),
    "weekend": dict(file="reference_weekend.html", date="Sat Nov 28",
                    lead="A quiet Saturday after a loud week for chips.",
                    rest="Rain clears by noon. Killington opens more terrain, and the Warriors try to snap a three-game skid.",
                    desc=dict(day="Cloudy until noon, one birthday today.",
                              bell="Crypto as of Friday's 4pm close.",
                              big="Why Nvidia's beat wasn't enough for the AI trade.",
                              top3="A Fed nominee, a chip export rule and a big bank deal.",
                              latest="Quick hits across business, tech, world, culture and sports.",
                              clock="Early ski terrain and one thing worth doing this weekend.",
                              memes="Four from today's feeds.")),
}

def build(edition):
    e = EDITIONS[edition]
    d = e["desc"]
    parts = []
    parts.append(f'''<tr><td class="px" style="padding:0 24px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
<td class="c-primary" style="font-family:{SANS};font-size:20px;line-height:27px;font-weight:500;letter-spacing:-0.01em;color:{T["primary"]};">The 7AM</td>
<td align="right" class="c-secondary" style="font-family:{MONO};font-size:14px;line-height:19px;letter-spacing:0.02em;text-transform:uppercase;color:{T["secondary"]};">{e["date"]}</td>
</tr></table></td></tr>''')
    parts.append(h1(e["lead"], e["rest"]))
    parts += your_day(edition, d["day"])
    parts += before_the_bell(edition, d["bell"])
    if edition != "weekend":
        parts += earnings(edition, d["earnings"])
        parts += holdings(edition, d["holdings"])
    parts += big_read(d["big"]) + top_3(d["top3"]) + latest(edition, d["latest"])
    parts += off_the_clock(d["clock"]) + memes(d["memes"])
    parts += footer()

    return f'''<!DOCTYPE html>
<!--
  The 7AM: reference issue ({edition} edition). Visual source of truth for templates/email.html.j2.
  SAMPLE CONTENT ONLY. Every number, headline and link is placeholder text for layout.
  Generated by build_reference.py. Tokens and rules: DESIGN_SYSTEM.md.
-->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>The 7AM</title>
<style>
  body {{ margin:0; padding:0; }}
  @media (max-width: 480px) {{
    .px {{ padding-left:16px !important; padding-right:16px !important; }}
    .t-title {{ font-size:22px !important; line-height:25px !important; }}
    .t-heading {{ font-size:18px !important; line-height:24px !important; }}
    .card {{ border-radius:8px !important; }}
  }}
  @media (prefers-color-scheme: dark) {{
    .bg {{ background-color:#0B0B0B !important; }}
    .card, .meme-ph {{ background-color:#1A1A1A !important; }}
    .c-primary {{ color:#F2F2F2 !important; }}
    .c-secondary {{ color:#9A9A9A !important; }}
    .c-theme {{ color:#4FB3E3 !important; }}
    .c-up {{ color:#3DD6A8 !important; }}
    .c-down {{ color:#FF6B6B !important; }}
    .b-subtle {{ border-color:#2A2A2A !important; }}
    .pill {{ background-color:#2A2A2A !important; color:#9A9A9A !important; }}
    .tpill {{ background-color:#0F2A38 !important; border-color:#1F5E7D !important; color:#F2F2F2 !important; }}
  }}
</style>
</head>
<body class="bg" style="margin:0;padding:0;background-color:{T["bg"]};">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;font-size:1px;line-height:1px;color:{T["bg"]};">{e["lead"]}&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="bg" style="background-color:{T["bg"]};">
<tr><td align="center" style="padding:32px 0 32px 0;">
<table role="presentation" width="552" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:552px;">
{"".join(parts)}
</table>
</td></tr>
</table>
</body>
</html>
'''

if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    os.makedirs(out_dir, exist_ok=True)
    for name, e in EDITIONS.items():
        doc = build(name)
        with open(os.path.join(out_dir, e["file"]), "w") as f:
            f.write(doc)
        print(f'{e["file"]}: {len(doc.encode())} bytes')
