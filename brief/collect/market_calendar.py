"""NYSE trading days, closures and early closes (exchange_calendars, XNYS).

Also the one place that decides which closes the market numbers compare against,
so markets.py, earnings.py and crypto all use the same dates.
"""
from datetime import date, datetime, time, timedelta
from functools import lru_cache

import pandas as pd

from brief import fmt
from brief.common import ET

# exchange_calendars' holiday names that read badly in the closure sentence (checked against
# exchange_calendars 4.x, Nov 27, 2026). Any other name is used as is ("Thanksgiving", "Good Friday").
HOLIDAY_NAMES = {
    "Dr. Martin Luther King Jr. Day": "Martin Luther King Jr. Day",
    "President's Day": "Presidents' Day",
    "Juneteenth National Independence Day": "Juneteenth",
    "July 4th": "the Fourth of July",
}


@lru_cache(maxsize=1)
def _cal():
    import exchange_calendars as xcals
    return xcals.get_calendar("XNYS")


def _d(ts) -> date:
    return pd.Timestamp(ts).date()


def is_session(d: date) -> bool:
    return bool(_cal().is_session(pd.Timestamp(d)))


def session_close_et(d: date) -> datetime:
    return _cal().session_close(pd.Timestamp(d)).tz_convert(ET).to_pydatetime()


def sessions_between(start: date, end: date) -> list[date]:
    """Trading days from start to end, inclusive."""
    return [_d(s) for s in _cal().sessions_in_range(pd.Timestamp(start), pd.Timestamp(end))]


def last_closed_session(now: datetime) -> date:
    """The most recent trading day whose close has already happened."""
    for s in reversed(sessions_between(now.date() - timedelta(days=15), now.date())):
        if session_close_et(s) <= now:
            return s
    raise RuntimeError("no trading session in the last 15 days")


def previous_session(d: date) -> date:
    return _d(_cal().previous_session(pd.Timestamp(d)))


def next_session_after(d: date) -> date:
    """First trading day strictly after d (d itself may be a weekend or holiday)."""
    for s in sessions_between(d + timedelta(days=1), d + timedelta(days=15)):
        return s
    raise RuntimeError("no trading session in the next 15 days")


def reference_sessions(now: datetime) -> dict:
    """The dates every market number is measured from.

    last:  the latest 4pm close (Friday on weekends and Monday mornings)
    prev:  the close before it (1D % base)
    week:  last trading day of the week before `last` (WTD % base). On Tuesday this is
           the Friday before, so WTD equals 1D. Decided, no special case.
    year:  last trading day of the previous year (YTD % base, Monday issue)
    """
    last = last_closed_session(now)
    monday = last - timedelta(days=last.weekday())
    week = last_session_before(monday)
    year = last_session_before(date(last.year, 1, 1))
    return {"last": last, "prev": previous_session(last), "week": week, "year": year}


def last_session_before(d: date) -> date:
    """Last trading day strictly before d (d may be a weekend or holiday)."""
    return sessions_between(d - timedelta(days=15), d - timedelta(days=1))[-1]


def _holiday_names(start: date, end: date) -> dict[date, str]:
    cal = _cal()
    names = {}
    if cal.regular_holidays is not None:
        s = cal.regular_holidays.holidays(pd.Timestamp(start), pd.Timestamp(end), return_name=True)
        for ts, name in s.items():
            names[_d(ts)] = HOLIDAY_NAMES.get(name, name)
    return names


def week_events(today: date) -> list[dict]:
    """Closures and early closes from today through Sunday of this week."""
    end = today + timedelta(days=6 - today.weekday())
    names = _holiday_names(today, end)
    out = []
    d = today
    while d <= end:
        if d.weekday() < 5:
            if not is_session(d):
                out.append({"date": d.isoformat(), "kind": "closed", "name": names.get(d)})
            else:
                close = session_close_et(d).time()
                if close != time(16, 0):
                    out.append({"date": d.isoformat(), "kind": "early_close", "close": fmt.hour(close.hour, close.minute)})
        d += timedelta(days=1)
    return out


def closure_line(today: date, events: list[dict]) -> str | None:
    """Fixed sentence render.py appends to the Before the bell description.

    "Markets close Thursday for Thanksgiving, early close Friday at 1pm."
    """
    if not events:
        return None
    parts = []
    for i, e in enumerate(events):
        d = date.fromisoformat(e["date"])
        day = "today" if d == today else d.strftime("%A")
        if e["kind"] == "closed":
            verb = ("are closed" if d == today else "close") if i == 0 else "closed"
            parts.append(f"{verb} {day}" + (f" for {e['name']}" if e.get("name") else ""))
        else:
            parts.append((f"close early {day}" if i == 0 else f"early close {day}") + f" at {e['close']}")
    return "Markets " + ", ".join(parts) + "."


def collect(cfg: dict, now: datetime) -> dict:
    today = now.date()
    refs = reference_sessions(now)
    events = week_events(today)
    return {
        "today_is_trading_day": is_session(today),
        "last_close": refs["last"].isoformat(),
        "this_week": events,
        "closure_line": closure_line(today, events),
    }
