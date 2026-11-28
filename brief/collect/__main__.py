"""python -m brief.collect [--now 2026-11-23T06:28]

Runs every collector and writes run/data.json. A collector that fails becomes
{"ok": false, "error": ...} and the rest keep going: the email always sends.
"""
import argparse
import json
import sys
import traceback
from datetime import datetime

from brief.common import ET, RUN_DIR, load_config, now_et
from brief.schema import Data

from . import earnings, market_calendar, markets, memes, mta, sports, weather

COLLECTORS = {
    "markets": markets.collect,
    "standout": markets.collect_standout,
    "earnings": earnings.collect,
    "market_calendar": market_calendar.collect,
    "weather": weather.collect,
    "mta": mta.collect,
    "sports": sports.collect,
    "memes": memes.collect,
}


def edition_for(now: datetime) -> str:
    wd = now.weekday()
    if wd >= 5:
        return "weekend"
    if wd == 0:
        return "monday"
    try:
        if not market_calendar.is_session(now.date()):
            return "holiday"
    except Exception:
        pass
    return "weekday"


def run_one(name, fn, cfg, now) -> dict:
    try:
        out = fn(cfg, now)
        out.setdefault("as_of", now.isoformat())
        return {"ok": True, **out}
    except Exception as e:
        print(f"[collect] {name} failed: {e}", file=sys.stderr)
        traceback.print_exc(limit=2, file=sys.stderr)
        return {"ok": False, "as_of": now.isoformat(), "error": f"{type(e).__name__}: {e}"}


def collect(now: datetime, cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    data = {"date": now.date().isoformat(), "edition": edition_for(now), "generated_at": now.isoformat()}
    for name, fn in COLLECTORS.items():
        data[name] = run_one(name, fn, cfg, now)
    Data.model_validate(data)          # catch shape mistakes here, not at render time
    return data


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--now", help="pretend it is this ET time, e.g. 2026-11-23T06:28")
    p.add_argument("--out", default=str(RUN_DIR / "data.json"))
    a = p.parse_args()
    now = datetime.fromisoformat(a.now).replace(tzinfo=ET) if a.now else now_et()
    data = collect(now)
    RUN_DIR.mkdir(exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    failed = [k for k in COLLECTORS if not data[k]["ok"]]
    print(f"wrote {a.out} ({data['edition']}); failed: {', '.join(failed) or 'none'}")


if __name__ == "__main__":
    main()
