"""Earnings results and calendar (Finnhub /calendar/earnings, free key).

Universe: every S&P 500 company, plus Wilson's holdings (config big_earnings_universe;
'top_50_sp500_by_market_cap' is still supported). Rows are sorted biggest first.
  reported   the previous trading day's reporters, with surprise % on revenue and EPS
             and the after-hours move (latest extended-hours price vs that day's close)
  next_day   who reports on the next trading day, and the sentence render.py appends
             ("Deere reports tomorrow." / "Dell and Salesforce report Monday.")
  week       Monday through Friday of this week, company names per day (Monday issue)
"""
import os
from datetime import date, datetime, time, timedelta

from brief import sp500
from brief.collect.market_calendar import next_session_after, reference_sessions, sessions_between
from brief.common import ET, get_json, pct

FINNHUB = "https://finnhub.io/api/v1/calendar/earnings"


# ---------- fetching (network) ----------

def fetch_calendar(start: date, end: date) -> list[dict]:
    key = os.environ.get("FINNHUB_API_KEY")
    if not key:
        raise RuntimeError("FINNHUB_API_KEY is not set")
    data = get_json(FINNHUB, params={"from": start.isoformat(), "to": end.isoformat()},
                    headers={"X-Finnhub-Token": key})
    return data.get("earningsCalendar", [])


def fetch_extended_prices(tickers: list[str]) -> dict[str, list[tuple[datetime, float]]]:
    """5-minute bars including pre- and post-market, as (time in ET, close)."""
    import yfinance as yf

    if not tickers:
        return {}
    df = yf.download(tickers, period="5d", interval="5m", prepost=True, progress=False,
                     auto_adjust=False)
    out = {}
    close = df["Close"]
    for t in tickers:
        col = close[t] if hasattr(close, "columns") and t in close.columns else close
        out[t] = [(ts.tz_convert(ET).to_pydatetime(), float(v)) for ts, v in col.dropna().items()]
    return out


# ---------- pure logic (tested) ----------

def norm(sym: str) -> str:
    return sym.replace(".", "-").upper()


def surprise(actual, estimate) -> float | None:
    """(actual - estimate) / |estimate|, as a percent rounded to 0.1. Positive = beat."""
    if actual is None or estimate in (None, 0):
        return None
    return round((actual - estimate) / abs(estimate) * 100, 1)


def after_hours_move(bars: list[tuple[datetime, float]], close_at: datetime) -> float | None:
    """Latest extended-hours price vs the regular close, as a percent."""
    before = [p for t, p in bars if t < close_at]
    after = [p for t, p in bars if t >= close_at]
    if not before or not after:
        return None
    return pct(after[-1], before[-1])


def join_names(names: list[str]) -> str:
    if len(names) <= 2:
        return " and ".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def next_line(names: list[str], today: date, next_day: date) -> str | None:
    if not names:
        return None
    when = "tomorrow" if next_day == today + timedelta(days=1) else next_day.strftime("%A")
    verb = "reports" if len(names) == 1 else "report"
    return f"{join_names(names)} {verb} {when}."


def rows_for(cal: list[dict], d: date, universe: dict[str, str]) -> list[dict]:
    return [r for r in cal if r.get("date") == d.isoformat() and norm(r["symbol"]) in universe]


def by_size(rows: list[dict], rank: dict[str, int]) -> list[dict]:
    return sorted(rows, key=lambda r: rank.get(norm(r["symbol"]), 999))


# ---------- collector ----------

def collect(cfg: dict, now: datetime) -> dict:
    today = now.date()
    refs = reference_sessions(now)
    rows = sp500.load()
    ranked = sorted(rows, key=lambda r: r["market_cap"], reverse=True)
    names = {r["ticker"]: r["name"] for r in rows}
    size = 50 if cfg["markets"].get("big_earnings_universe") == "top_50_sp500_by_market_cap" else len(ranked)
    universe = {r["ticker"]: r["name"] for r in ranked[:size]}
    for h in cfg["markets"]["holdings"]:
        universe[h] = names.get(h, h)
    rank = {r["ticker"]: i for i, r in enumerate(ranked)}

    monday = today - timedelta(days=today.weekday())
    nxt = next_session_after(today)
    cal = fetch_calendar(min(refs["last"], monday), max(nxt, monday + timedelta(days=4)))

    reported_raw = by_size([r for r in rows_for(cal, refs["last"], universe)
                            if r.get("epsActual") is not None or r.get("revenueActual") is not None], rank)
    ext = fetch_extended_prices([norm(r["symbol"]) for r in reported_raw])
    close_at = datetime.combine(refs["last"], time(16, 0), ET)
    reported = []
    for r in reported_raw:
        t = norm(r["symbol"])
        reported.append({
            "ticker": t,
            "name": universe[t],
            "timing": r.get("hour") or None,          # bmo, amc, dmh
            "revenue_actual": r.get("revenueActual"),
            "revenue_estimate": r.get("revenueEstimate"),
            "revenue_surprise_pct": surprise(r.get("revenueActual"), r.get("revenueEstimate")),
            "eps_actual": r.get("epsActual"),
            "eps_estimate": r.get("epsEstimate"),
            "eps_surprise_pct": surprise(r.get("epsActual"), r.get("epsEstimate")),
            "after_hours_pct": after_hours_move(ext.get(t, []), close_at),
        })

    next_names = [universe[norm(r["symbol"])] for r in by_size(rows_for(cal, nxt, universe), rank)]
    week = []
    for d in sessions_between(monday, monday + timedelta(days=4)):
        n = [universe[norm(r["symbol"])] for r in by_size(rows_for(cal, d, universe), rank)]
        if n:
            week.append({"date": d.isoformat(), "day": d.strftime("%a"), "names": n})

    return {
        "as_of": now.isoformat(),
        "reported_date": refs["last"].isoformat(),
        "reported": reported,
        "next_day": {"date": nxt.isoformat(), "names": next_names,
                     "line": next_line(next_names, today, nxt)},
        "week": week,
    }
