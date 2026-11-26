"""Writes the sample issues in tests/fixtures/issues/<name>/ (data, calendar, content).

They reuse the placeholder content from build_reference.py, so a rendered fixture can be
compared one-to-one with templates/reference_*.html. Run: python tests/fixtures/build_fixtures.py
Names: weekday, monday, weekend (the three references), birthday and unavailable (the two
states that were never mocked up, BUILD_PLAN.md §14).
"""
import copy
import json
from pathlib import Path

OUT = Path(__file__).parent / "issues"
CLOSURE = "Markets close Thursday for Thanksgiving, early close Friday at 1pm."


def q(symbol, label, price, d1, wtd, ytd):
    return {"symbol": symbol, "label": label, "price": price, "change_1d_pct": d1, "wtd_pct": wtd, "ytd_pct": ytd}


def data(date, edition, ts):
    return {
        "date": date, "edition": edition, "generated_at": ts,
        "markets": {"ok": True, "as_of": ts, "close_date": date,
                    "indices": [q("^GSPC", "S&P 500", 6812.40, -0.62, -0.62, 14.80),
                                q("^DJI", "Dow", 46890.12, -0.21, -0.21, 10.47),
                                q("^IXIC", "Nasdaq", 23104.77, -1.08, -1.08, 19.42)],
                    "crypto": [q("BTC-USD", "Bitcoin", 97420, 1.84, 3.10 if edition == "weekend" else 1.84, 4.95),
                               q("ETH-USD", "Ether", 3512, 0.0, -1.25 if edition == "weekend" else 0.0, -6.30)],
                    "holdings": [q("GOOGL", "GOOGL", 312.48, 0.92, 0.92, 38.20), q("PLTR", "PLTR", 186.10, -3.17, -3.17, 141.05),
                                 q("GEV", "GEV", 642.05, 1.40, 1.40, 92.64), q("COST", "COST", 958.30, 0.15, 0.15, 4.71),
                                 q("V", "V", 348.72, -0.44, -0.44, 10.33), q("GS", "GS", 812.66, 0.58, 0.58, 41.90),
                                 q("SOXX", "SOXX", 284.15, -2.31, -2.31, 22.06)]},
        "standout": {"ok": True, "as_of": ts, "ticker": "NVDA", "name": "Nvidia", "price": 160.2,
                     "change_1d_pct": -6.40, "universe_size": 107,
                     "movers": [{"ticker": "NVDA", "name": "Nvidia", "price": 160.2, "change_1d_pct": -6.40},
                                {"ticker": "WMT", "name": "Walmart", "price": 104.85, "change_1d_pct": 4.12},
                                {"ticker": "AVGO", "name": "Broadcom", "price": 331.40, "change_1d_pct": -3.87},
                                {"ticker": "AMD", "name": "AMD", "price": 214.05, "change_1d_pct": -3.55}]},
        "earnings": {"ok": True, "as_of": ts, "reported_date": "2026-11-23", "reported": [
            {"ticker": "NVDA", "name": "Nvidia", "timing": "amc", "revenue_actual": 57.0e9, "revenue_estimate": 55.18e9,
             "revenue_surprise_pct": 3.3, "eps_actual": 1.30, "eps_estimate": 1.25, "eps_surprise_pct": 4.0, "after_hours_pct": -6.40},
            {"ticker": "WMT", "name": "Walmart", "timing": "bmo", "revenue_actual": 179.5e9, "revenue_estimate": 180.04e9,
             "revenue_surprise_pct": -0.3, "eps_actual": 0.62, "eps_estimate": 0.60, "eps_surprise_pct": 3.3, "after_hours_pct": 2.10}],
            "next_day": {"date": "2026-11-25", "names": ["Deere"], "line": "Deere reports tomorrow."},
            "week": [{"date": "2026-11-23", "day": "Mon", "names": ["Zoom Communications"]},
                     {"date": "2026-11-24", "day": "Tue", "names": ["Dell Technologies", "Salesforce"]},
                     {"date": "2026-11-25", "day": "Wed", "names": ["Deere"]}]},
        "market_calendar": {"ok": True, "as_of": ts, "today_is_trading_day": edition != "weekend",
                            "closure_line": None if edition == "weekend" else CLOSURE,
                            "this_week": [] if edition == "weekend" else [
                                {"date": "2026-11-26", "kind": "closed", "name": "Thanksgiving"},
                                {"date": "2026-11-27", "kind": "early_close", "close": "1pm"}]},
        "weather": {"ok": True, "as_of": ts, "location": "New York", "temp_now": 48, "high": 53, "low": 41, "code": 3,
                    "conditions": "Cloudy", "icon": "cloud", "summary": "Cloudy, high 53°, low 41°.",
                    "outlook": "Cloudy until 4pm, then rain", "precip": "Rain likely after 4pm."},
        "mta": {"ok": True, "as_of": ts, "lines": ["4", "5"], "alerts": [] if edition == "weekend" else [
            {"lines": ["4", "5"], "type": "Delays", "text": "Delays in both directions after a signal problem at Grand Central.",
             "planned": False, "systemwide": False}]},
        "sports": {"ok": True, "as_of": ts, "since": ts, "results": [
            {"league": "NFL", "team": "49ers", "opponent": "Packers", "team_score": 27, "opponent_score": 20, "result": "W",
             "home": True, "start": "2026-11-23T20:15:00-05:00"},
            {"league": "NBA", "team": "Warriors", "opponent": "Lakers", "team_score": 108, "opponent_score": 115, "result": "L",
             "home": False, "start": "2026-11-23T22:00:00-05:00"}],
            "week": [] if edition != "monday" else [
                {"league": "NBA", "team": "Warriors", "opponent": "Rockets", "home": True, "day": "Wed",
                 "start": "2026-11-25T19:30:00-05:00", "time": "7:30pm"},
                {"league": "NFL", "team": "49ers", "opponent": "Seahawks", "home": True, "day": "Thu",
                 "start": "2026-11-26T20:20:00-05:00", "time": "8:20pm"}]},
        "memes": {"ok": True, "as_of": ts, "candidates": [
            {"url": f"https://i.redd.it/sample{i}.jpg", "title": f"Sample meme {i}", "community": "memes", "score": 5000 - i,
             "permalink": f"https://www.reddit.com/r/memes/{i}", "width": 1000, "height": [1200, 952, 1000, 800][i % 4]}
            for i in range(1, 7)]},
    }


def link(title, source, url):
    return {"title": title, "source": source, "url": url}


def story(h, body, source, url, title="Sample article"):
    return {"headline": h, "body": body, "link": link(title, source, url)}


DESC = {
    "weekday": dict(your_day="Cloudy with rain after 4pm, 4/5 delays, lunch at 12:30.",
                    before_the_bell="Chips led a down day for the Nasdaq.",
                    earnings="Nvidia beat on both lines and still fell after hours. Walmart missed on revenue.",
                    holdings="A mixed day. PLTR and GOOGL both had news.",
                    big_read="Why Nvidia's beat wasn't enough for the AI trade.",
                    top_3="A Fed nominee, a chip export rule and a big bank deal.",
                    latest="Quick hits across business, tech, world, culture and sports.",
                    off_the_clock="Early ski terrain and one thing worth doing this week.",
                    memes="Four from today's feeds."),
}
DESC["monday"] = {**DESC["weekday"], "your_day": "Cloudy with rain after 4pm and a short week ahead.",
                  "before_the_bell": "Chips closed last week on a down note.",
                  "earnings": "A light holiday week. Zoom tonight, then Dell and Salesforce Tuesday.",
                  "holdings": "PLTR leads the year. PLTR and GOOGL both had news this weekend.",
                  "memes": "Four from the weekend's feeds."}
DESC["weekend"] = {**DESC["weekday"], "your_day": "Cloudy until noon, one birthday today.",
                   "before_the_bell": "Crypto as of Friday's 4pm close.",
                   "off_the_clock": "Early ski terrain and one thing worth doing this weekend."}
for k in ("earnings", "holdings"):
    DESC["weekend"].pop(k)

INTRO = {
    "weekday": "Nvidia beat on every line and the stock still fell. Chips dragged the Nasdaq lower and took the S&P with it. "
               "Markets close Thursday for Thanksgiving, so expect a thin week.",
    "monday": "Nvidia beat on every line and the stock still fell. Chips dragged the Nasdaq into Friday's close. "
              "Thanksgiving week starts quiet, with markets shut Thursday.",
    "weekend": "A quiet Saturday after a loud week for chips. Rain clears by noon. Killington opens more terrain, "
               "and the Warriors try to snap a three-game skid.",
}


def content(date, edition):
    weekend = edition == "weekend"
    return {
        "date": date, "edition": edition, "subject": "Nvidia beat, and it still wasn't enough.",
        "intro": INTRO[edition], "section_desc": DESC[edition],
        "your_day_nyc": [link("Congestion pricing revenue tops projections for the third straight month", "NYT",
                              "https://www.nytimes.com/2026/11/23/nyregion/congestion-pricing.html"),
                         link("Rockefeller Center tree lighting set for December 2", "Gothamist",
                              "https://gothamist.com/news/rockefeller-tree-lighting"),
                         link("Knicks host the Celtics at the Garden tonight", "ESPN",
                              "https://www.espn.com/nba/story/knicks-celtics")],
        "movers": [] if weekend else [
            {"ticker": "NVDA",
             "body": "Record quarter on every line, but data center guidance came in under what investors were hoping for. "
                     "It pulled the rest of the chip sector down with it.",
             "link": link("Nvidia falls despite record quarter", "WSJ", "https://www.wsj.com/tech/nvidia-earnings-guidance")},
            {"ticker": "WMT",
             "body": "Placeholder. Holiday sales guidance came in ahead of the street and traffic rose for a sixth quarter.",
             "link": link("Walmart raises its holiday outlook", "CNBC", "https://www.cnbc.com/2026/11/23/walmart-outlook.html")},
            {"ticker": "AVGO",
             "body": "Placeholder. Sold off alongside Nvidia as investors pulled back from AI chip names.",
             "link": link("Chip stocks slide after Nvidia guidance", "Reuters", "https://www.reuters.com/markets/chips-slide")}],
        "on_deck_today": [] if weekend else [{"time": "8:30", "text": "Chicago Fed national activity index"},
                                             {"time": "2:00", "text": "Fed governor speaks on bank capital rules"}],
        "holdings_news": [] if weekend else [
            {**story("PLTR: Army expands its software contract",
                     "Placeholder. Two to three sentences on what happened and why it matters to the position. Any number comes from data.json, never from the article.",
                     "WSJ", "https://www.wsj.com/business/palantir-army-contract"), "ticker": "PLTR"},
            {**story("GOOGL: Gemini update ships to Workspace customers",
                     "Placeholder. A second holding with news. Every holding with relevant, recent news gets a story, as many as the day calls for.",
                     "NYT", "https://www.nytimes.com/2026/11/23/technology/gemini-workspace.html"), "ticker": "GOOGL"}],
        "big_read": story("Sample headline: the AI trade hits its first real test",
                          "Placeholder paragraph one. About 300 words across three or four short paragraphs, in the Morning Brew shape: what happened, the context, why it matters, what to watch.\n\n"
                          "Placeholder paragraph two. Short declarative sentences. Strong verbs. Numbers over adjectives. No jokes, no em dashes, no filler.\n\n"
                          "Why it matters: Placeholder paragraph three. One medium-weight lead-in in black marks the takeaway.",
                          "NYT", "https://www.nytimes.com/2026/11/23/business/ai-trade-test.html"),
        "top_3": [{**story("Sample story one headline with a verb", "Placeholder. About 100 words: the news first, then context, then why it matters.",
                           "Reuters", "https://www.reuters.com/markets/sample-one"), "emoji": "🏦"},
                  {**story("Sample story two headline with a verb", "Placeholder. Same shape, different beat: markets, tech, world.",
                           "WSJ", "https://www.wsj.com/economy/sample-two"), "emoji": "💾"},
                  {**story("Sample story three headline with a verb", "Placeholder. If it needs more than 120 words, it belongs in The Big Read.",
                           "BBC", "https://www.bbc.com/news/sample-three"), "emoji": "🌍"}],
        "latest": {
            "business": [link("Sample headline about a deal or Wall Street move", "WSJ", "https://www.wsj.com/finance/deal"),
                         link("Sample headline: Goldman news kept to one line", "CNBC", "https://www.cnbc.com/2026/11/23/goldman.html"),
                         link("Sample headline about the Fed", "Reuters", "https://www.reuters.com/markets/fed")],
            "tech": [link("Sample headline about a model launch", "The Verge", "https://www.theverge.com/ai/model-launch"),
                     link("Sample headline about big tech regulation", "NYT", "https://www.nytimes.com/2026/11/23/technology/regulation.html")],
            "world": [link("Sample world headline", "AP", "https://apnews.com/article/world-sample"),
                      link("Sample politics headline", "BBC", "https://www.bbc.com/news/politics-sample")],
            "pop_culture": [link("Sample box office headline", "Variety", "https://variety.com/2026/film/box-office"),
                            link("Sample music or streaming headline", "NYT", "https://www.nytimes.com/2026/11/23/arts/music.html")],
            "sports": [link("Sample headline: star quarterback out for the season with a torn ACL", "ESPN", "https://www.espn.com/nfl/story/qb-acl"),
                       link("Sample headline about a big NFL trade", "ESPN", "https://www.espn.com/nfl/story/trade"),
                       link("Sample Giants offseason headline", "The Athletic", "https://www.nytimes.com/athletic/giants-offseason")],
        },
        "off_the_clock": [{**story("Ski report: Killington opens more terrain this weekend",
                                   "Placeholder. Base depth, lifts open, snow in the forecast.", "NYT",
                                   "https://www.nytimes.com/2026/11/23/travel/killington-ski.html"), "emoji": "⛷️"},
                          {**story("Cars: Rivian opens R2 test drives",
                                   "Placeholder. What it is, why it's worth a look.", "The Verge",
                                   "https://www.theverge.com/cars/rivian-r2-test-drives"), "emoji": "🚙"}],
        "memes": [f"https://i.redd.it/sample{i}.jpg" for i in range(1, 5)],
    }


def calendar(date, edition):
    today = [{"start": f"{date}T12:30:00-05:00", "all_day": False, "title": "Team lunch", "location": "200 West St", "kind": "event"},
             {"start": None, "all_day": True, "title": "Sample Friend's birthday", "kind": "birthday"}]
    if edition == "weekend":
        today = today[1:]
    week = [] if edition != "monday" else [
        {"start": "2026-11-24T10:00:00-05:00", "title": "Design review", "kind": "event"},
        {"start": "2026-11-25T18:15:00-05:00", "title": "Flight to SFO", "kind": "event"},
        {"start": "2026-11-26T00:00:00-05:00", "all_day": True, "title": "Thanksgiving", "kind": "holiday"}]
    return {"date": date, "today": today, "this_week": week}


ISSUES = {"weekday": ("2026-11-24", "weekday"), "monday": ("2026-11-23", "monday"), "weekend": ("2026-11-28", "weekend")}


def write(name, d, cal, c):
    folder = OUT / name
    folder.mkdir(parents=True, exist_ok=True)
    for fname, obj in (("data.json", d), ("calendar.json", cal), ("content.json", c)):
        (folder / fname).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def main():
    for name, (date, edition) in ISSUES.items():
        ts = f"{date}T06:41:00-05:00"
        write(name, data(date, edition, ts), calendar(date, edition), content(date, edition))
    # Wilson's own birthday: a weekday with a "Happy birthday!" event.
    d, cal, c = data("2026-11-24", "weekday", "2026-11-24T06:41:00-05:00"), calendar("2026-11-24", "weekday"), content("2026-11-24", "weekday")
    cal["today"].insert(0, {"start": None, "all_day": True, "title": "Happy birthday!", "kind": "own_birthday"})
    write("birthday", d, cal, c)
    # Unavailable: markets, earnings, weather and memes failed; no calendar file.
    d = data("2026-11-24", "weekday", "2026-11-24T06:41:00-05:00")
    for k in ("markets", "standout", "earnings", "weather", "memes"):
        d[k] = {"ok": False, "as_of": d["generated_at"], "error": "RuntimeError: sample failure"}
    c = content("2026-11-24", "weekday")
    c["memes"] = []
    write("unavailable", d, None, c)


if __name__ == "__main__":
    main()
