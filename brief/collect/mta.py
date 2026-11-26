"""Subway alerts for Wilson's lines (MTA GTFS-RT alerts as JSON, no key).

Only alerts active right now that name one of config.subway_lines, and only ones that
touch Wilson's ride (config.subway_stops, Fulton St to Union Sq):
  - an alert whose text says it is somewhere else ("In the Bronx, ...", "In Brooklyn, ...")
    never counts;
  - an alert that lists stations counts only if one of them is on the ride;
  - an alert with no stations (live delays, "5 runs every 20 minutes") counts.
Header text only, max 2. Unplanned problems (delays, suspensions) come before planned work.
"""
import re
from datetime import datetime

from brief.common import get_json

URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fsubway-alerts.json"
MAX_ALERTS = 2


def _english(texts: dict) -> str:
    for t in (texts or {}).get("translation", []):
        if t.get("language") == "en":
            return t["text"]
    return ""


def clean(text: str) -> str:
    """MTA writes routes as [4] or [4][5][6]. Write them as plain text: 4 / 4, 5, 6."""
    text = re.sub(r"((?:\[[A-Z0-9]+\])+)", lambda m: ", ".join(re.findall(r"\[([A-Z0-9]+)\]", m.group(1))), text)
    return re.sub(r"\s+", " ", text).strip()


def is_active(alert: dict, ts: int) -> bool:
    periods = alert.get("active_period") or [{}]
    return any(p.get("start", 0) <= ts < p.get("end", 2**40) for p in periods)


ELSEWHERE = re.compile(r"^\s*In (the Bronx|Brooklyn|Queens)\b", re.I)


def on_my_ride(alert: dict, text: str, stops: set[str] | None) -> bool:
    """True if the alert could touch the ride (see the module docstring)."""
    if not stops:
        return True
    if ELSEWHERE.match(text):              # the MTA's own scope wins, even if it lists the whole line
        return False
    listed = {str(x["stop_id"]).rstrip("NS") for x in alert.get("informed_entity", []) if x.get("stop_id")}
    return bool(listed & stops) if listed else True


def parse(feed: dict, lines: list[str], now: datetime, stops: set[str] | None = None) -> list[dict]:
    ts = int(now.timestamp())
    found = []
    for e in feed.get("entity", []):
        a = e.get("alert") or {}
        routes = {x.get("route_id") for x in a.get("informed_entity", [])}
        mine = sorted(routes & set(lines))
        if not mine or not is_active(a, ts):
            continue
        kind = (a.get("transit_realtime.mercury_alert") or {}).get("alert_type", "")
        text = clean(_english(a.get("header_text")))
        if not text or any(f["text"] == text for f in found) or not on_my_ride(a, text, stops):
            continue
        found.append({"lines": mine, "type": kind, "text": text,
                      "planned": kind.lower().startswith("planned"),
                      "systemwide": len(routes) > 10})
    # Unplanned first, then planned work, system-wide notices (holiday schedules) last.
    found.sort(key=lambda f: (f["systemwide"], f["planned"]))
    return found[:MAX_ALERTS]


def collect(cfg: dict, now: datetime) -> dict:
    return {"as_of": now.isoformat(), "lines": cfg["subway_lines"],
            "alerts": parse(get_json(URL), cfg["subway_lines"], now, set(cfg.get("subway_stops") or {}))}
