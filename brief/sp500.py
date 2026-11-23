"""The S&P 500 list in data/sp500.csv (ticker, name, market_cap, updated).

Market caps are stored here and refreshed monthly, so the morning run only needs one
small price request instead of ~500 lookups (fewer chances for Yahoo to block us).

Refresh: python -m brief.sp500
Source for the constituent list: github.com/datasets/s-and-p-500-companies (plain CSV).
"""
import csv
import io
import sys
import time
from datetime import date

import requests

from brief.common import ROOT, USER_AGENT

CSV_PATH = ROOT / "data" / "sp500.csv"
SOURCE = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"

# Shorter, everyday names for the Earnings section ("Deere reports tomorrow.").
SUFFIXES = [" & Company", " & Co.", ", Inc.", " Inc.", " Inc", " Corporation", " Corp.", " Corp", " Company", " Co.",
            " Incorporated", " plc", " PLC", " Ltd.", " Ltd", " N.V.", " Holdings",
            " Group", " (The)", " (Class A)", " (Class B)", " (Class C)"]
# Names the list writes "Last (First)", like "Lilly (Eli)".
RENAMES = {"Lilly (Eli)": "Eli Lilly"}


def yahoo_ticker(sym: str) -> str:
    return sym.replace(".", "-")   # BRK.B -> BRK-B


def short_name(name: str) -> str:
    name = RENAMES.get(name, name)
    for _ in range(3):
        for s in SUFFIXES:
            if name.endswith(s):
                name = name[: -len(s)].rstrip(",")
    return name.strip().removesuffix(" &").strip()   # "Deere &" saved by an older refresh


def load() -> list[dict]:
    with open(CSV_PATH) as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["market_cap"] = float(r["market_cap"]) if r["market_cap"] else 0.0
        r["name"] = short_name(r["name"])
    # One row per company: Alphabet (GOOGL/GOOG), Fox and News Corp list two share
    # classes. Keep the bigger one, so Alphabet is GOOGL, matching the holdings.
    best = {}
    for r in rows:
        if r["name"] not in best or r["market_cap"] > best[r["name"]]["market_cap"]:
            best[r["name"]] = r
    return [r for r in rows if best[r["name"]] is r]


def top_by_cap(n: int) -> list[dict]:
    return sorted(load(), key=lambda r: r["market_cap"], reverse=True)[:n]


def refresh() -> None:
    import yfinance as yf

    text = requests.get(SOURCE, headers={"User-Agent": USER_AGENT}, timeout=30).text
    src = list(csv.DictReader(io.StringIO(text)))
    out = []
    for i, r in enumerate(src):
        t = yahoo_ticker(r["Symbol"])
        cap = None
        for attempt in range(3):
            try:
                cap = yf.Ticker(t).fast_info["marketCap"]
                break
            except Exception:
                time.sleep(2)
        out.append({"ticker": t, "name": short_name(r["Security"]),
                    "market_cap": int(cap) if cap else "", "updated": date.today().isoformat()})
        if i % 50 == 0:
            print(f"{i}/{len(src)}", file=sys.stderr)
    CSV_PATH.parent.mkdir(exist_ok=True)
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ticker", "name", "market_cap", "updated"])
        w.writeheader()
        w.writerows(out)
    missing = sum(1 for r in out if not r["market_cap"])
    print(f"wrote {len(out)} rows to {CSV_PATH} ({missing} without market cap)")


if __name__ == "__main__":
    refresh()
