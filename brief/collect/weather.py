"""East Village weather. Open-Meteo /v1/forecast (no key), and if that fails, the National
Weather Service (api.weather.gov, no key) as a backup (Wilson, Nov 27, 2026).

Why a backup: the morning task runs on shared cloud servers, and Open-Meteo's free limit is
per internet address, so other people's traffic can get us a 429 "Too Many Requests" (that
blanked the weather on Nov 27). The Weather Service is a separate system. Its hourly
descriptions ("Chance Rain Showers") are translated to the same WMO codes Open-Meteo uses,
so both produce the same fields and the same weather line.

temp_now   the big theme-color number in Your day, the temperature when the task runs
summary    "Cloudy, high 53°, low 41°."
outlook    "Foggy until 10am, then partly cloudy" (from the hourly codes, now through 11pm)
precip     "Rain likely after 4pm." / "Snow likely until 11am." / "Rain likely all day." / None
icon       the SF Symbol for today's WMO weather code, as Apple Weather picks it:
           sun, partly, cloud, fog, drizzle, rain, snow or storm
"""
import re
from datetime import datetime

from brief import fmt
from brief.common import get_json

URL = "https://api.open-meteo.com/v1/forecast"
NWS = "https://api.weather.gov"
LIKELY = 50          # % chance of precipitation that counts as "likely"
DAY_HOURS = range(6, 24)

CONDITIONS = {
    0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Cloudy", 45: "Foggy", 48: "Foggy",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle", 56: "Freezing drizzle", 57: "Freezing drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain", 66: "Freezing rain", 67: "Freezing rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow",
    80: "Rain showers", 81: "Rain showers", 82: "Heavy rain showers", 85: "Snow showers", 86: "Snow showers",
    95: "Thunderstorms", 96: "Thunderstorms with hail", 99: "Thunderstorms with hail",
}
SNOW_CODES = set(range(71, 78)) | {85, 86}


def kind_for(code: int) -> str:
    """WMO code -> one of the icon names, which double as the outlook's condition groups."""
    if code in (0, 1):
        return "sun"
    if code == 2:
        return "partly"
    if code in (45, 48):
        return "fog"
    if 51 <= code <= 57:
        return "drizzle"
    if code in SNOW_CODES:
        return "snow"
    if 61 <= code <= 67 or 80 <= code <= 82:
        return "rain"
    if 95 <= code <= 99:
        return "storm"
    return "cloud"


OUTLOOK_WORDS = {"sun": "Sunny", "partly": "Partly cloudy", "cloud": "Cloudy", "fog": "Foggy",
                 "drizzle": "Drizzle", "rain": "Rain", "snow": "Snow", "storm": "Thunderstorms"}
MIN_SPELL = 2        # hours; a shorter change of conditions is folded into its neighbor


def outlook_line(hours: list[int], codes: list[int], now_hour: int) -> str | None:
    """'Foggy until 10am, then partly cloudy': today's conditions from now through 11pm,
    at most three spells, each at least MIN_SPELL hours."""
    day = [(h, kind_for(c)) for h, c in zip(hours, codes) if h >= max(now_hour, DAY_HOURS.start)]
    if not day:
        return None
    spells: list[list] = []                      # [kind, first hour, hours]
    for h, k in day:
        if spells and spells[-1][0] == k:
            spells[-1][2] += 1
        else:
            spells.append([k, h, 1])
    changed = True
    while changed and len(spells) > 1:           # fold short spells into the previous one
        changed = False
        for i, sp in enumerate(spells):
            if sp[2] < MIN_SPELL:
                j = i - 1 if i > 0 else 1
                spells[j][2] += sp[2]
                spells[j][1] = min(spells[j][1], sp[1])
                del spells[i]
                merged = []
                for x in spells:                 # neighbors may now match
                    if merged and merged[-1][0] == x[0]:
                        merged[-1][2] += x[2]
                    else:
                        merged.append(x)
                spells = merged
                changed = True
                break
    spells = spells[:3]
    words = ["Clear" if k == "sun" and h >= 18 else OUTLOOK_WORDS[k] for k, h, _ in spells]
    if len(spells) == 1:
        return words[0]
    parts = [f"{words[0]} until {fmt.hour(spells[1][1])}"]
    for i in range(1, len(spells)):
        w = words[i].lower()
        parts.append(f"then {w} until {fmt.hour(spells[i + 1][1])}" if i + 1 < len(spells) else f"then {w}")
    return ", ".join(parts)


def precip_line(hours: list[int], probs: list[int], codes: list[int], now_hour: int) -> str | None:
    """One short sentence about when rain or snow is likely today, or None."""
    day = [(h, p or 0, c) for h, p, c in zip(hours, probs, codes) if h in DAY_HOURS and h >= now_hour]
    likely = [h for h, p, c in day if p >= LIKELY]
    if not likely:
        return None
    kind = "Snow" if any(c in SNOW_CODES for h, p, c in day if p >= LIKELY) else "Rain"
    first = likely[0]
    if first <= max(now_hour, DAY_HOURS.start):
        dry = [h for h, p, c in day if h > first and p < LIKELY]
        if not dry:
            return f"{kind} likely all day."
        return f"{kind} likely until {fmt.hour(dry[0])}."
    return f"{kind} likely after {fmt.hour(first)}."


def parse(data: dict, now: datetime) -> dict:
    d = data["daily"]
    code = int(d["weather_code"][0])
    hi, lo = round(d["temperature_2m_max"][0]), round(d["temperature_2m_min"][0])
    today = now.date().isoformat()
    h = data["hourly"]
    idx = [i for i, t in enumerate(h["time"]) if t.startswith(today)]
    hours = [int(h["time"][i][11:13]) for i in idx]
    cond = CONDITIONS.get(code, "Cloudy")
    return {
        "temp_now": round(data["current"]["temperature_2m"]),
        "high": hi,
        "low": lo,
        "code": code,
        "conditions": cond,
        "icon": kind_for(code),
        "outlook": outlook_line(hours, [h["weather_code"][i] for i in idx], now.hour),
        "summary": f"{cond}, high {hi}°, low {lo}°.",
        "precip": precip_line(hours, [h["precipitation_probability"][i] for i in idx],
                              [h["weather_code"][i] for i in idx], now.hour),
    }


# ---------- National Weather Service backup ----------

def nws_code(short: str) -> int:
    """A Weather Service hourly description as the WMO code Open-Meteo would give.
    "Chance" / "Slight Chance" (under 50%) means it probably won't, so those hours count as cloudy."""
    t = short.lower()
    if "chance" in t and "likely" not in t:
        return 3
    if "thunder" in t:
        return 95
    if re.search(r"snow|flurr|sleet|wintry|ice pellets", t):
        return 73
    if "freezing" in t:
        return 66
    if "drizzle" in t:
        return 53
    if "rain" in t or "shower" in t:
        return 61 if "light" in t else 63
    if re.search(r"fog|haze|smoke|mist", t):
        return 45
    if t in ("sunny", "clear", "mostly sunny", "mostly clear"):
        return 0 if t in ("sunny", "clear") else 1
    if t in ("partly sunny", "partly cloudy"):
        return 2
    return 3                                     # mostly cloudy, cloudy, overcast, anything new


def parse_nws(hourly: dict, now: datetime, daily: dict | None = None) -> dict:
    """Today's hours from the Weather Service's hourly forecast, in the same shape as parse().
    The hourly forecast starts at the current hour, so the high also checks the daily forecast's
    "Today" high, and the low is the coolest hour left (at 6:30am that's close to the day's low)."""
    today = [p for p in hourly["properties"]["periods"]
             if datetime.fromisoformat(p["startTime"]).date() == now.date()]
    if not today:
        raise RuntimeError("Weather Service returned no hours for today")
    hours = [datetime.fromisoformat(p["startTime"]).hour for p in today]
    codes = [nws_code(p["shortForecast"]) for p in today]
    probs = [(p.get("probabilityOfPrecipitation") or {}).get("value") or 0 for p in today]
    temps = [p["temperature"] if p.get("temperatureUnit", "F") == "F" else round(p["temperature"] * 9 / 5 + 32)
             for p in today]
    day = [c for h, c in zip(hours, codes) if h in DAY_HOURS] or codes
    code = max(day)                              # like Open-Meteo's daily code: the day's most severe weather
    day_high = [p["temperature"] for p in (daily or {}).get("properties", {}).get("periods", [])
                if p.get("isDaytime") and datetime.fromisoformat(p["startTime"]).date() == now.date()]
    hi, lo, cond = max(temps + day_high[:1]), min(temps), CONDITIONS.get(code, "Cloudy")
    return {
        "temp_now": temps[0],                    # the forecast for the current hour
        "high": hi, "low": lo, "code": code, "conditions": cond, "icon": kind_for(code),
        "outlook": outlook_line(hours, codes, now.hour),
        "summary": f"{cond}, high {hi}°, low {lo}°.",
        "precip": precip_line(hours, probs, codes, now.hour),
    }


def collect_nws(loc: dict, now: datetime) -> dict:
    point = get_json(f"{NWS}/points/{loc['lat']:.4f},{loc['lon']:.4f}")
    hourly = get_json(point["properties"]["forecastHourly"], headers={"Accept": "application/geo+json"})
    try:
        daily = get_json(point["properties"]["forecast"], headers={"Accept": "application/geo+json"})
    except Exception:
        daily = None                             # the hourly forecast alone is enough
    return parse_nws(hourly, now, daily)


def collect(cfg: dict, now: datetime) -> dict:
    loc = cfg["location"]
    base = {"location": loc["name"]}
    try:
        return {**base, "source": "open-meteo", **collect_open_meteo(loc, cfg["timezone"], now)}
    except Exception as first:
        try:
            return {**base, "source": "nws", **collect_nws(loc, now)}
        except Exception as second:
            raise RuntimeError(f"Open-Meteo: {first}; Weather Service: {second}") from second


def collect_open_meteo(loc: dict, tz: str, now: datetime) -> dict:
    data = get_json(URL, params={
        "latitude": loc["lat"], "longitude": loc["lon"],
        "current": "temperature_2m,weather_code",
        "daily": "temperature_2m_max,temperature_2m_min,weather_code",
        "hourly": "precipitation_probability,weather_code",
        "temperature_unit": "fahrenheit", "timezone": tz, "forecast_days": 1,
    })
    return parse(data, now)
