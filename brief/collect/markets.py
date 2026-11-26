"""Indices, ETF, crypto and holdings prices, plus the standout stock (yfinance).

Every number is measured at a 4pm ET close (see market_calendar.reference_sessions):
  price   the latest 4pm close
  1D %    vs the 4pm close before it
  WTD %   vs the last close of the previous week
  YTD %   vs the last close of last year (shown on Mondays instead of WTD)
Crypto uses the same 4pm ET moments, read from hourly bars, not a rolling 24h window.
"""
from datetime import date, datetime, time, timedelta

from brief import sp500
from brief.collect.market_calendar import reference_sessions
from brief.common import ET, pct


# ---------- fetching (network) ----------

def fetch_daily_closes(symbols: list[str], start: date, end: date) -> dict[str, dict[date, float]]:
    """Official daily closes, {symbol: {session date: close}}."""
    import yfinance as yf

    df = yf.download(symbols, start=start.isoformat(), end=(end + timedelta(days=1)).isoformat(),
                     interval="1d", auto_adjust=False, progress=False, threads=True)
    if df is None or df.empty:
        raise RuntimeError("Yahoo returned no daily data")
    close = df["Close"]
    out = {}
    for s in symbols:
        col = close[s] if hasattr(close, "columns") and s in close.columns else close
        out[s] = {ts.date(): float(v) for ts, v in col.dropna().items()}
    return out


def fetch_hourly(symbol: str, start: date) -> list[tuple[datetime, float, float]]:
    """Hourly bars as (start time in ET, open, close)."""
    import yfinance as yf

    df = yf.download(symbol, start=start.isoformat(), interval="1h", auto_adjust=False,
                     progress=False)
    if df is None or df.empty:
        raise RuntimeError(f"Yahoo returned no hourly data for {symbol}")
    opens, closes = df["Open"], df["Close"]
    if hasattr(opens, "columns"):
        opens, closes = opens[symbol], closes[symbol]
    return [(ts.tz_convert(ET).to_pydatetime(), float(o), float(c))
            for ts, o, c in zip(df.index, opens, closes) if o == o and c == c]


# ---------- pure logic (tested) ----------

def price_at_4pm(bars: list[tuple[datetime, float, float]], d: date) -> float | None:
    """Price at 16:00 ET on day d: the open of the 16:00 bar, else the close of the 15:00 bar."""
    target = datetime.combine(d, time(16, 0), ET)
    for start, o, c in bars:
        if start == target:
            return o
    for start, o, c in bars:
        if start == target - timedelta(hours=1):
            return c
    return None


def row(symbol: str, label: str, prices: dict[date, float], refs: dict) -> dict:
    last = prices.get(refs["last"])
    if last is None:
        raise RuntimeError(f"{symbol}: no price for {refs['last']}")
    return {
        "symbol": symbol,
        "label": label,
        "price": round(last, 2),
        "change_1d_pct": pct(last, prices.get(refs["prev"])),
        "wtd_pct": pct(last, prices.get(refs["week"])),
        "ytd_pct": pct(last, prices.get(refs["year"])),
    }


def pick_movers(closes: dict[str, dict[date, float]], refs: dict, names: dict[str, str], n: int = 8) -> list[dict]:
    """The n biggest absolute 1-day moves among the big names, biggest first."""
    out = []
    for t, prices in closes.items():
        p = pct(prices.get(refs["last"]), prices.get(refs["prev"]))
        if p is not None:
            out.append({"ticker": t, "name": names.get(t, t), "change_1d_pct": p,
                        "price": round(prices[refs["last"]], 2)})
    return sorted(out, key=lambda r: abs(r["change_1d_pct"]), reverse=True)[:n]


def pick_standout(closes: dict[str, dict[date, float]], refs: dict, names: dict[str, str]) -> dict | None:
    """Biggest absolute 1-day move among the big names."""
    top = pick_movers(closes, refs, names, 1)
    return top[0] if top else None


# ---------- collectors ----------

def collect(cfg: dict, now: datetime) -> dict:
    m = cfg["markets"]
    refs = reference_sessions(now)
    start = refs["year"] - timedelta(days=7)

    stock_syms = [i["symbol"] for i in m["indices"]] + m["holdings"]
    closes = fetch_daily_closes(stock_syms, start, refs["last"])

    crypto = []
    for c in m["crypto"]:
        bars = fetch_hourly(c["symbol"], start)
        prices = {d: price_at_4pm(bars, d) for d in {refs["last"], refs["prev"], refs["week"], refs["year"]}}
        crypto.append(row(c["symbol"], c["label"], {k: v for k, v in prices.items() if v}, refs))

    return {
        "as_of": datetime.combine(refs["last"], time(16, 0), ET).isoformat(),
        "close_date": refs["last"].isoformat(),
        "indices": [row(i["symbol"], i["label"], closes[i["symbol"]], refs) for i in m["indices"]],
        "crypto": crypto,
        "holdings": [row(t, t, closes[t], refs) for t in m["holdings"]],
    }


def collect_standout(cfg: dict, now: datetime) -> dict:
    refs = reference_sessions(now)
    big = [r for r in sp500.load() if r["market_cap"] >= cfg["markets"]["standout_min_market_cap"]]
    names = {r["ticker"]: r["name"] for r in big}
    closes = fetch_daily_closes(list(names), refs["prev"] - timedelta(days=5), refs["last"])
    movers = pick_movers(closes, refs, names, cfg["markets"].get("movers_shortlist", 8))
    if not movers:
        raise RuntimeError("no 1-day moves found")
    # Top-level fields are the single biggest mover; `movers` is the shortlist Claude picks 2-3 from.
    return {"as_of": datetime.combine(refs["last"], time(16, 0), ET).isoformat(),
            "universe_size": len(names), **movers[0], "movers": movers}
