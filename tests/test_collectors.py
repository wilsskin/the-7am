"""Collector logic, tested against saved real responses in tests/fixtures (no network)."""
import json
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pytest

from brief.collect import earnings, market_calendar as mc, markets, memes, mta, sports, weather
from brief.common import ET

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIX / name).read_text())


def et(y, m, d, h=6, mi=22):
    return datetime(y, m, d, h, mi, tzinfo=ET)


# ---------- market calendar (Thanksgiving week 2026: closed Thu 26, early close Fri 27) ----------

def test_reference_sessions_tuesday():
    r = mc.reference_sessions(et(2026, 11, 24))
    assert r == {"last": date(2026, 11, 23), "prev": date(2026, 11, 20),
                 "week": date(2026, 11, 20), "year": date(2025, 12, 31)}   # Tuesday: WTD == 1D


def test_reference_sessions_monday_uses_friday():
    r = mc.reference_sessions(et(2026, 11, 23))
    assert r["last"] == date(2026, 11, 20) and r["prev"] == date(2026, 11, 19)
    assert r["week"] == date(2026, 11, 13)


def test_reference_sessions_saturday_after_early_close():
    r = mc.reference_sessions(et(2026, 11, 28))
    assert r["last"] == date(2026, 11, 27) and r["prev"] == date(2026, 11, 25)


def test_before_4pm_uses_previous_close():
    assert mc.last_closed_session(et(2026, 11, 24, 15, 59)) == date(2026, 11, 23)
    assert mc.last_closed_session(et(2026, 11, 24, 16, 0)) == date(2026, 11, 24)


def test_closure_line_monday():
    today = date(2026, 11, 23)
    assert mc.closure_line(today, mc.week_events(today)) == \
        "Markets close Thursday for Thanksgiving, early close Friday at 1pm."


def test_closure_line_on_the_holiday():
    today = date(2026, 11, 26)
    assert mc.closure_line(today, mc.week_events(today)) == \
        "Markets are closed today for Thanksgiving, early close Friday at 1pm."


def test_no_closure_line_normal_week():
    today = date(2026, 12, 1)
    assert mc.week_events(today) == [] and mc.closure_line(today, []) is None


def test_edition():
    from brief.collect.__main__ import edition_for
    assert edition_for(et(2026, 11, 23)) == "monday"
    assert edition_for(et(2026, 11, 24)) == "weekday"
    assert edition_for(et(2026, 11, 26)) == "holiday"
    assert edition_for(et(2026, 11, 28)) == "weekend"


# ---------- markets ----------

REFS = {"last": date(2026, 11, 23), "prev": date(2026, 11, 20), "week": date(2026, 11, 20), "year": date(2025, 12, 31)}


def test_row_percentages():
    prices = {REFS["last"]: 110.0, REFS["prev"]: 100.0, REFS["year"]: 50.0}
    r = markets.row("X", "X", prices, REFS)
    assert r["price"] == 110.0 and r["change_1d_pct"] == 10.0 and r["wtd_pct"] == 10.0 and r["ytd_pct"] == 120.0


def test_row_missing_last_close_fails():
    with pytest.raises(RuntimeError):
        markets.row("X", "X", {REFS["prev"]: 1.0}, REFS)


def test_crypto_price_at_4pm_et():
    d = date(2026, 11, 20)
    bars = [(datetime.combine(d, time(h), ET), float(h), float(h) + 0.5) for h in range(12, 19)]
    assert markets.price_at_4pm(bars, d) == 16.0          # open of the 16:00 bar
    no_16 = [b for b in bars if b[0].hour != 16]
    assert markets.price_at_4pm(no_16, d) == 15.5         # else close of the 15:00 bar
    assert markets.price_at_4pm([], d) is None


def test_movers_shortlist_sorted_by_absolute_move():
    closes = {"AAA": {REFS["prev"]: 100, REFS["last"]: 103},
              "BBB": {REFS["prev"]: 100, REFS["last"]: 93.6},
              "DDD": {REFS["prev"]: 100, REFS["last"]: 100.5},
              "CCC": {REFS["prev"]: 100}}
    ms = markets.pick_movers(closes, REFS, {}, 2)
    assert [m["ticker"] for m in ms] == ["BBB", "AAA"]


def test_standout_is_biggest_absolute_move():
    closes = {"AAA": {REFS["prev"]: 100, REFS["last"]: 103},
              "BBB": {REFS["prev"]: 100, REFS["last"]: 93.6},
              "CCC": {REFS["prev"]: 100}}
    s = markets.pick_standout(closes, REFS, {"BBB": "Bravo"})
    assert s["ticker"] == "BBB" and s["name"] == "Bravo" and s["change_1d_pct"] == -6.4


# ---------- earnings ----------

def test_surprise():
    assert earnings.surprise(57.0, 55.18) == 3.3
    assert earnings.surprise(-0.5, -1.0) == 50.0          # smaller loss is a beat
    assert earnings.surprise(1.0, None) is None and earnings.surprise(1.0, 0) is None


def test_next_line():
    tue = date(2026, 11, 24)
    assert earnings.next_line(["Deere"], tue, date(2026, 11, 25)) == "Deere reports tomorrow."
    fri = date(2026, 11, 20)
    assert earnings.next_line(["Dell", "Salesforce"], fri, date(2026, 11, 23)) == "Dell and Salesforce report Monday."
    assert earnings.next_line(["A", "B", "C"], tue, date(2026, 11, 25)) == "A, B and C report tomorrow."
    assert earnings.next_line([], tue, date(2026, 11, 25)) is None


def test_after_hours_move():
    close_at = datetime(2026, 11, 23, 16, 0, tzinfo=ET)
    bars = [(close_at - timedelta(minutes=5), 100.0), (close_at + timedelta(hours=1), 95.0),
            (close_at + timedelta(hours=14), 93.6)]
    assert earnings.after_hours_move(bars, close_at) == -6.4
    assert earnings.after_hours_move(bars[:1], close_at) is None


def test_norm_matches_yahoo_tickers():
    assert earnings.norm("BRK.B") == "BRK-B"


# ---------- weather ----------

def test_weather_parse_fixture():
    w = weather.parse(load("openmeteo.json"), et(2026, 11, 22))
    assert isinstance(w["temp_now"], int) and w["high"] >= w["low"]
    assert w["icon"] in {"sun", "partly", "cloud", "fog", "drizzle", "rain", "snow", "storm"}
    assert w["summary"].endswith(f"high {w['high']}°, low {w['low']}°.")


@pytest.mark.parametrize("code,icon", [(0, "sun"), (1, "sun"), (2, "partly"), (3, "cloud"), (45, "fog"), (48, "fog"),
                                       (51, "drizzle"), (61, "rain"), (67, "rain"), (80, "rain"), (95, "storm"),
                                       (71, "snow"), (77, "snow"), (85, "snow")])
def test_icon_for(code, icon):
    assert weather.icon_for(code) == icon


def test_outlook_line():
    hours = list(range(24))
    assert weather.outlook_line(hours, [45] * 10 + [2] * 14, 6) == "Foggy until 10am, then partly cloudy"
    assert weather.outlook_line(hours, [3] * 16 + [61] * 5 + [2] * 3, 6) == \
        "Cloudy until 4pm, then rain until 9pm, then partly cloudy"
    assert weather.outlook_line(hours, [3] * 24, 6) == "Cloudy"
    # A one-hour blip folds into its neighbor.
    assert weather.outlook_line(hours, [0] * 12 + [61] + [0] * 11, 6) == "Sunny"


def test_precip_line():
    hours = list(range(24))
    rain_after_4 = [80 if h >= 16 else 10 for h in hours]
    assert weather.precip_line(hours, rain_after_4, [61] * 24, 6) == "Rain likely after 4pm."
    until_11 = [80 if h < 11 else 10 for h in hours]
    assert weather.precip_line(hours, until_11, [61] * 24, 6) == "Rain likely until 11am."
    assert weather.precip_line(hours, [90] * 24, [73] * 24, 6) == "Snow likely all day."
    assert weather.precip_line(hours, [10] * 24, [3] * 24, 6) is None


# ---------- MTA ----------

def test_mta_fixture_only_active_4_5_max_two():
    feed = load("mta_alerts.json")
    now = datetime.fromtimestamp(int(feed["header"]["timestamp"]), ET)
    alerts = mta.parse(feed, ["4", "5"], now)
    assert len(alerts) <= 2
    for a in alerts:
        assert set(a["lines"]) & {"4", "5"} and "[" not in a["text"]


def test_mta_clean_route_brackets():
    assert mta.clean("In Manhattan, downtown [4][5][6] skip 86 St") == "In Manhattan, downtown 4, 5, 6 skip 86 St"
    assert mta.clean("[5] runs every 20 minutes") == "5 runs every 20 minutes"


def test_mta_unplanned_first():
    def alert(route, kind, text):
        return {"alert": {"active_period": [{"start": 0}], "informed_entity": [{"route_id": route}],
                          "header_text": {"translation": [{"language": "en", "text": text}]},
                          "transit_realtime.mercury_alert": {"alert_type": kind}}}
    feed = {"entity": [alert("4", "Planned - Stops Skipped", "planned"), alert("6", "Delays", "other line"),
                       alert("5", "Delays", "[5] trains are delayed")]}
    out = mta.parse(feed, ["4", "5"], et(2026, 11, 24))
    assert [a["text"] for a in out] == ["5 trains are delayed", "planned"]


def test_mta_only_alerts_on_my_ride():
    def alert(text, stops=(), route="4", kind="Planned - Stops Skipped"):
        ie = [{"route_id": route}] + [{"route_id": route, "stop_id": st} for st in stops]
        return {"alert": {"active_period": [{"start": 0}], "informed_entity": ie,
                          "header_text": {"translation": [{"language": "en", "text": text}]},
                          "transit_realtime.mercury_alert": {"alert_type": kind}}}
    ride = {"418", "640", "635"}
    feed = {"entity": [
        alert("In the Bronx, Manhattan-bound [4] skips 176 St", ["408", "410"]),
        alert("No [5] between E 180 St, Bronx and Bowling Green, Manhattan", ["416", "418", "420"], "5"),
        alert("In Manhattan, downtown [4][5][6] skip 86 St", ["626"]),
        alert("In the Bronx, [4] runs every 16 minutes", [], kind="Reduced Service"),
        alert("In the Bronx, [4] runs every 20 minutes", ["401", "418", "640"], kind="Reduced Service"),
        alert("Downtown [4] trains are running with delays", [], kind="Delays")]}
    out = mta.parse(feed, ["4", "5"], et(2026, 11, 24), ride)
    assert [a["text"] for a in out] == ["Downtown 4 trains are running with delays",
                                        "No 5 between E 180 St, Bronx and Bowling Green, Manhattan"]


# ---------- sports ----------

def test_find_team():
    assert sports.find_team(load("espn_nba_teams.json"), "Golden State Warriors") == {"id": "9", "short": "Warriors"}


def test_results_from_scoreboard():
    teams = load("espn_nba_teams.json")
    knicks = sports.find_team(teams, "New York Knicks")
    now = et(2026, 11, 22)
    r = sports.results(load("espn_nba_scoreboard.json"), knicks["id"], "nba", now - sports.WINDOW, now)
    assert len(r) == 1
    g = r[0]
    assert (g["team"], g["team_score"], g["opponent_score"], g["result"]) == ("Knicks", 97, 96, "W")
    # Outside the window: nothing.
    later = et(2026, 11, 24)
    assert sports.results(load("espn_nba_scoreboard.json"), knicks["id"], "nba", later - sports.WINDOW, later) == []


def test_week_games_monday_to_sunday():
    monday = datetime(2026, 11, 23, tzinfo=ET)
    g = sports.week_games(load("espn_gs_schedule.json"), "9", "nba", monday)
    assert [x["day"] for x in g] == ["Wed", "Fri", "Sun"]
    assert g[0]["opponent"] == "Kings" and g[0]["home"] and g[0]["time"] == "10pm"
    assert not g[1]["home"]


# ---------- memes ----------

def test_reddit_meme_candidates_filter():
    def post(**kw):
        base = {"url": "https://i.redd.it/a.jpg", "score": 1000, "over_18": False, "title": "a &amp; b",
                "subreddit": "memes", "permalink": "/r/memes/1"}
        base.update(kw)
        return {"data": base}
    listing = {"data": {"children": [post(), post(over_18=True), post(score=10),
                                     post(url="https://i.redd.it/x.gif"), post(url="https://example.com/a.jpg")]}}
    out = memes.reddit_candidates(listing, 500)
    assert len(out) == 1 and out[0]["title"] == "a & b" and out[0]["community"] == "memes"


def test_lemmy_meme_candidates_filter():
    def post(score=300, community_nsfw=False, **kw):
        p = {"name": "a &amp; b", "url": "https://lemmy.world/pictrs/image/a.png", "nsfw": False,
             "removed": False, "deleted": False, "ap_id": "https://lemmy.world/post/1"}
        p.update(kw)
        return {"post": p, "counts": {"score": score}, "community": {"name": "memes", "nsfw": community_nsfw}}
    listing = {"posts": [post(), post(nsfw=True), post(community_nsfw=True), post(score=10),
                         post(url="https://lemmy.world/pictrs/image/x.gif"), post(url="https://youtube.com/watch?v=1"),
                         post(url="http://insecure.example/a.jpg"), post(featured_community=True), post(removed=True),
                         post(url="https://sh.itjust.works/pictrs/image/b.webp?format=webp")]}
    out = memes.lemmy_candidates(listing, 100)
    assert [o["url"] for o in out] == ["https://lemmy.world/pictrs/image/a.png",
                                       "https://sh.itjust.works/pictrs/image/b.webp?format=webp"]
    assert out[0] == {"url": "https://lemmy.world/pictrs/image/a.png", "title": "a & b", "community": "memes",
                      "score": 300, "permalink": "https://lemmy.world/post/1", "width": None, "height": None}


SS_PAGE = """<h1>Top Reads</h1><img src="https://media.beehiiv.com/cdn-cgi/image/q=80/uploads/asset/file/aaa/notmeme.png" width="10" height="10">
<h1><span>Memes of the Day</span></h1>
<picture><img src="https://media.beehiiv.com/cdn-cgi/image/fit=scale-down,format=auto/uploads/asset/file/m1/image.png?t=1" alt="" width="1206" height="1511"/></picture>
<img src="https://media.beehiiv.com/cdn-cgi/image/fit=scale-down/uploads/asset/file/m1/image.png?t=1" width="1206" height="1511"/>
<img src="https://media.beehiiv.com/cdn-cgi/image/fit=scale-down/uploads/asset/file/m2/image.gif?t=1"/>
<img src="https://other.example/x.png"/>
<img alt="" src="https://media.beehiiv.com/cdn-cgi/image/w=1/uploads/asset/file/m3/photo.JPG"/>
<p>Partner With Us</p><img src="https://media.beehiiv.com/cdn-cgi/image/x/uploads/asset/file/ad/ad.png"/>"""


def test_newsletter_section_images():
    imgs = memes.section_images(SS_PAGE, "Memes of the Day", ("Partner With Us",))
    base = "https://media.beehiiv.com/cdn-cgi/image/fit=scale-down,format=auto,quality=80,width=1008,onerror=redirect/"
    assert imgs == [{"url": base + "uploads/asset/file/m1/image.png", "width": 1206, "height": 1511},
                    {"url": base + "uploads/asset/file/m3/photo.JPG", "width": None, "height": None}]
    assert memes.section_images(SS_PAGE, "Meme Cleanser") == []          # heading missing: nothing


def test_newsletter_freshness():
    from datetime import datetime, timezone
    now = datetime(2026, 11, 25, 11, 28, tzinfo=timezone.utc)             # 6:28am ET
    assert memes.fresh(datetime(2026, 11, 25, 9, 0, tzinfo=timezone.utc), now, 26)      # today's 4am issue
    assert memes.fresh(datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc), now, 26)     # yesterday's 7am issue
    assert not memes.fresh(datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc), now, 26)  # already sent
    assert not memes.fresh(datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc), now, 26)  # future


def test_one_failing_meme_source_is_skipped(monkeypatch):
    def boom(m, now):
        raise RuntimeError("site down")
    monkeypatch.setitem(memes.SOURCES, "shortsqueez", boom)
    monkeypatch.setitem(memes.SOURCES, "lemmy", lambda m, now: [{"url": "https://a/1.png"}, {"url": "https://a/1.png"}])
    out = memes.collect({"memes": {"sources": ["shortsqueez", "lemmy"]}}, datetime(2026, 11, 25))
    assert out["sources"] == ["lemmy"] and out["candidates"] == [{"url": "https://a/1.png"}]
    assert out["source_errors"][0].startswith("shortsqueez: RuntimeError")
    monkeypatch.setitem(memes.SOURCES, "lemmy", boom)
    with pytest.raises(RuntimeError):
        memes.collect({"memes": {"sources": ["shortsqueez", "lemmy"]}}, datetime(2026, 11, 25))


def test_meme_interleave():
    assert memes.interleave([[1, 2, 3], ["a"], ["x", "y"]]) == [1, "a", "x", 2, "y", 3]


def test_company_short_names():
    from brief import sp500
    assert sp500.short_name("Deere & Company") == "Deere"
    assert sp500.short_name("Deere &") == "Deere"
    assert sp500.short_name("Home Depot (The)") == "Home Depot"
    assert sp500.short_name("Lilly (Eli)") == "Eli Lilly"
    assert sp500.short_name("Apple Inc.") == "Apple"
    names = [r["name"] for r in sp500.load()]
    assert not [n for n in names if n.endswith("&") or "(" in n]
