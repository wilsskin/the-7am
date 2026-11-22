"""East Village weather (Open-Meteo /v1/forecast, no key).

temp_now   the big theme-color number in Your day, the temperature when the task runs
summary    "Cloudy, high 53°, low 41°."
precip     "Rain likely after 4pm." / "Snow likely until 11am." / "Rain likely all day." / None
icon       sun, cloud, rain or snow, from today's WMO weather code
"""
from datetime import datetime

from brief.common import get_json

URL = "https://api.open-meteo.com/v1/forecast"
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


def icon_for(code: int) -> str:
    if code in (0, 1):
        return "sun"
    if code in SNOW_CODES:
        return "snow"
    if 51 <= code <= 67 or 80 <= code <= 82 or 95 <= code <= 99:
        return "rain"
    return "cloud"


def _hour_label(h: int) -> str:
    return f"{h % 12 or 12}{'am' if h < 12 else 'pm'}"


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
        return f"{kind} likely until {_hour_label(dry[0])}."
    return f"{kind} likely after {_hour_label(first)}."


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
        "icon": icon_for(code),
        "summary": f"{cond}, high {hi}°, low {lo}°.",
        "precip": precip_line(hours, [h["precipitation_probability"][i] for i in idx],
                              [h["weather_code"][i] for i in idx], now.hour),
    }


def collect(cfg: dict, now: datetime) -> dict:
    loc = cfg["location"]
    data = get_json(URL, params={
        "latitude": loc["lat"], "longitude": loc["lon"],
        "current": "temperature_2m,weather_code",
        "daily": "temperature_2m_max,temperature_2m_min,weather_code",
        "hourly": "precipitation_probability,weather_code",
        "temperature_unit": "fahrenheit", "timezone": cfg["timezone"], "forecast_days": 1,
    })
    return {"as_of": now.isoformat(), "location": loc["name"], **parse(data, now)}
