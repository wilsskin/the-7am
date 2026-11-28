"""Small shared helpers: config, time zone, HTTP."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
RUN_DIR = ROOT / "run"
ET = ZoneInfo("America/New_York")

# Generic client name. No personal details go to outside services.
USER_AGENT = "the-7am/0.1 (personal newsletter)"
TIMEOUT = 20


def load_config(path: Path | None = None) -> dict:
    with open(path or ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def now_et() -> datetime:
    return datetime.now(ET)


def get(url: str, params: dict | None = None, headers: dict | None = None) -> requests.Response:
    r = requests.get(url, params=params, headers={"User-Agent": USER_AGENT, **(headers or {})}, timeout=TIMEOUT)
    r.raise_for_status()
    return r


def get_json(url: str, params: dict | None = None, headers: dict | None = None):
    return get(url, params, headers).json()


def pct(new: float, base: float, decimals: int = 2) -> float | None:
    """Percent change, rounded. None if either side is missing. Earnings surprise uses 1 decimal:
    (actual - estimate) / |estimate|, so a smaller loss than expected is a beat."""
    if new is None or base in (None, 0):
        return None
    return round((new - base) / abs(base) * 100, decimals)
