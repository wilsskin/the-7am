"""Number and time formatting for the issue. Code owns every number's look.

move()   "+1.84%" / "−0.62%" / "0.00%", with the up/down/secondary color class
price()  "6,812.40" (crypto: "97,420")
big()    revenue: "57.0B", "850.3M", "1.2T"
"""
from datetime import datetime

MINUS = "−"   # real minus sign, never a hyphen (DESIGN_SYSTEM.md)


def signed(p: float, decimals: int) -> str:
    s = f"{abs(p):,.{decimals}f}"
    if round(p, decimals) == 0:
        return s
    return ("+" if p > 0 else MINUS) + s


def color(p: float | None, decimals: int = 2) -> str:
    if p is None or round(p, decimals) == 0:
        return "secondary"
    return "up" if p > 0 else "down"


def move(p: float | None, decimals: int = 2) -> dict:
    if p is None:
        return {"text": "—", "c": "secondary"}
    return {"text": signed(p, decimals) + "%", "c": color(p, decimals)}


def price(v: float, crypto: bool = False) -> str:
    return f"{v:,.0f}" if crypto else f"{v:,.2f}"


def big(v: float | None) -> str:
    if v is None:
        return "—"
    a = abs(v)
    for div, unit in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if a >= div:
            return (MINUS if v < 0 else "") + f"{a / div:.1f}{unit}"
    return f"{v:,.0f}"


def eps(v: float | None) -> str:
    if v is None:
        return "—"
    return (MINUS if v < 0 else "") + f"{abs(v):.2f}"


def hour(h: int, m: int = 0) -> str:
    """"1pm" / "1:30pm": early closes, game times, weather spells."""
    return f"{h % 12 or 12}{'' if m == 0 else f':{m:02d}'}{'am' if h < 12 else 'pm'}"


def clock(dt: datetime) -> str:
    """Calendar times as in the mockup: "12:30", "10:00", but "6:15pm" in the evening
    and "6:30am" early, where the hour alone would be ambiguous."""
    h12 = dt.hour % 12 or 12
    s = f"{h12}:{dt.minute:02d}"
    if dt.hour >= 18 or dt.hour < 7:
        s += "pm" if dt.hour >= 12 else "am"
    return s


def masthead_date(d) -> str:
    return d.strftime("%a %b ") + str(d.day)
