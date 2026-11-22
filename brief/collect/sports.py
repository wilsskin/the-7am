"""Scores and schedules for Wilson's teams (ESPN public JSON, no key).

results   followed teams' games that finished since the previous morning's run.
          Every edition uses the same window, Monday included (decided Nov 22, 2026:
          Monday only covers what happened since Sunday's issue).
week      Monday issue only: Monday through Sunday games for teams with week_preview.
"""
from datetime import datetime, timedelta

from brief.common import ET, get_json

BASE = "https://site.api.espn.com/apis/site/v2/sports"
PATHS = {"nfl": "football/nfl", "nba": "basketball/nba", "mlb": "baseball/mlb"}
# Look back one day, plus a margin so a game that started just before the last run
# but finished after it is still caught.
WINDOW = timedelta(hours=27)


def parse_time(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(ET)


def fmt_time(t: datetime) -> str:
    return f"{t.hour % 12 or 12}{'' if t.minute == 0 else f':{t.minute:02d}'}{'am' if t.hour < 12 else 'pm'}"


def find_team(teams_json: dict, display_name: str) -> dict:
    for t in teams_json["sports"][0]["leagues"][0]["teams"]:
        team = t["team"]
        if team["displayName"].lower() == display_name.lower():
            return {"id": team["id"], "short": team.get("shortDisplayName") or team["name"]}
    raise RuntimeError(f"team not found: {display_name}")


def _short(c: dict) -> str:
    t = c["team"]
    return t.get("shortDisplayName") or t.get("name") or t["displayName"]


def _score(c: dict):
    s = c.get("score")
    if isinstance(s, dict):
        s = s.get("value", s.get("displayValue"))
    return int(float(s)) if s not in (None, "") else None


def results(scoreboard: dict, team_id: str, league: str, since: datetime, now: datetime) -> list[dict]:
    out = []
    for ev in scoreboard.get("events", []):
        comp = ev["competitions"][0]
        if not ev.get("status", comp.get("status", {}))["type"].get("completed"):
            continue
        start = parse_time(ev["date"])
        if not (since <= start <= now):
            continue
        mine = [c for c in comp["competitors"] if c["team"]["id"] == team_id]
        if not mine:
            continue
        us = mine[0]
        them = [c for c in comp["competitors"] if c is not us][0]
        a, b = _score(us), _score(them)
        result = "W" if a > b else ("L" if a < b else "T")
        out.append({"league": league.upper(), "team": _short(us), "opponent": _short(them),
                    "team_score": a, "opponent_score": b, "result": result,
                    "home": us.get("homeAway") == "home", "start": start.isoformat()})
    return out


def week_games(schedule: dict, team_id: str, league: str, monday: datetime) -> list[dict]:
    end = monday + timedelta(days=7)
    out = []
    for ev in schedule.get("events", []):
        start = parse_time(ev["date"])
        if not (monday <= start < end):
            continue
        comp = ev["competitions"][0]
        us = [c for c in comp["competitors"] if str(c["team"]["id"]) == str(team_id)]
        them = [c for c in comp["competitors"] if str(c["team"]["id"]) != str(team_id)]
        if not us or not them:
            continue
        timed = comp.get("timeValid", True)
        out.append({"league": league.upper(), "team": _short(us[0]), "opponent": _short(them[0]),
                    "home": us[0].get("homeAway") == "home", "day": start.strftime("%a"),
                    "start": start.isoformat(), "time": fmt_time(start) if timed else "TBD"})
    return out


def collect(cfg: dict, now: datetime) -> dict:
    since = now - WINDOW
    # ESPN's scoreboard takes one date at a time (ranges return a 400).
    days = sorted({(since + timedelta(days=i)).strftime("%Y%m%d") for i in range(3)
                   if since + timedelta(days=i) <= now + timedelta(days=1)} | {now.strftime("%Y%m%d")})
    res, week = [], []
    for t in cfg["sports"]["teams"]:
        path = f"{BASE}/{PATHS[t['league']]}"
        team = find_team(get_json(f"{path}/teams", params={"limit": 50}), t["team"])
        seen = set()
        for d in days:
            for r in results(get_json(f"{path}/scoreboard", params={"dates": d}), team["id"], t["league"], since, now):
                if r["start"] not in seen:
                    seen.add(r["start"])
                    res.append(r)
        if now.weekday() == 0 and t.get("week_preview"):
            monday = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week += week_games(get_json(f"{path}/teams/{team['id']}/schedule"), team["id"], t["league"], monday)
    week.sort(key=lambda g: g["start"])
    return {"as_of": now.isoformat(), "since": since.isoformat(), "results": res, "week": week}
