"""Pydantic models for the three files a run produces (BUILD_PLAN.md §7).

data.json      written by the collectors (python -m brief.collect)
calendar.json  written by Claude from the Google Calendar connector
content.json   written by Claude: text and links only, no HTML, no markdown

Every data.json block has ok / as_of / error. A failed block keeps only those three,
and its section renders "... unavailable this morning."
"""
import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

Edition = Literal["weekday", "monday", "weekend", "holiday"]


# ---------- data.json ----------

class Block(BaseModel):
    ok: bool
    as_of: datetime | None = None
    error: str | None = None


class Quote(BaseModel):
    symbol: str
    label: str
    price: float
    change_1d_pct: float | None
    wtd_pct: float | None
    ytd_pct: float | None


class Markets(Block):
    close_date: date | None = None
    indices: list[Quote] = []
    crypto: list[Quote] = []
    holdings: list[Quote] = []


class Mover(BaseModel):
    ticker: str
    name: str
    price: float
    change_1d_pct: float


class Standout(Block):
    ticker: str | None = None
    name: str | None = None
    price: float | None = None
    change_1d_pct: float | None = None
    universe_size: int | None = None
    movers: list[Mover] = []                 # shortlist, biggest move first


class Reported(BaseModel):
    ticker: str
    name: str
    timing: str | None                       # bmo (before open), amc (after close), dmh
    revenue_actual: float | None
    revenue_estimate: float | None
    revenue_surprise_pct: float | None
    eps_actual: float | None
    eps_estimate: float | None
    eps_surprise_pct: float | None
    after_hours_pct: float | None


class NextDay(BaseModel):
    date: date
    names: list[str]
    line: str | None                         # appended to the Earnings description, Tue–Fri


class WeekDay(BaseModel):
    date: date
    day: str
    names: list[str]


class Earnings(Block):
    reported_date: date | None = None
    reported: list[Reported] = []
    next_day: NextDay | None = None
    week: list[WeekDay] = []


class MarketEvent(BaseModel):
    date: date
    kind: Literal["closed", "early_close"]
    name: str | None = None
    close: str | None = None


class MarketCalendar(Block):
    today_is_trading_day: bool | None = None
    last_close: date | None = None
    this_week: list[MarketEvent] = []
    closure_line: str | None = None          # appended to the Before the bell description


class Weather(Block):
    source: Literal["open-meteo", "nws"] | None = None   # nws = National Weather Service backup
    location: str | None = None
    temp_now: int | None = None
    high: int | None = None
    low: int | None = None
    code: int | None = None
    conditions: str | None = None
    icon: Literal["sun", "partly", "cloud", "fog", "drizzle", "rain", "snow", "storm"] | None = None
    summary: str | None = None
    outlook: str | None = None
    precip: str | None = None


class Alert(BaseModel):
    lines: list[str]
    type: str
    text: str
    planned: bool
    systemwide: bool


class Mta(Block):
    lines: list[str] = []
    alerts: list[Alert] = []


class GameResult(BaseModel):
    league: str
    team: str
    opponent: str
    team_score: int
    opponent_score: int
    result: Literal["W", "L", "T"]
    home: bool
    start: datetime


class Game(BaseModel):
    league: str
    team: str
    opponent: str
    home: bool
    day: str
    start: datetime
    time: str


class Sports(Block):
    since: datetime | None = None
    results: list[GameResult] = []
    week: list[Game] = []


class MemeCandidate(BaseModel):
    url: HttpUrl
    title: str
    community: str           # Lemmy community, subreddit, or newsletter name
    score: int | None = None  # upvotes; None for newsletter memes
    permalink: str
    width: int | None = None
    height: int | None = None


class Memes(Block):
    sources: list[str] = []
    source_errors: list[str] = []
    candidates: list[MemeCandidate] = []


class Data(BaseModel):
    date: date
    edition: Edition
    generated_at: datetime
    markets: Markets
    standout: Standout
    earnings: Earnings
    market_calendar: MarketCalendar
    weather: Weather
    mta: Mta
    sports: Sports
    memes: Memes


# ---------- calendar.json ----------

class Event(BaseModel):
    start: datetime | None = None
    all_day: bool = False
    title: str
    location: str | None = None
    kind: Literal["event", "birthday", "own_birthday", "holiday"] = "event"


class Calendar(BaseModel):
    date: date
    today: list[Event] = []
    this_week: list[Event] = []              # Mondays only


# ---------- content.json ----------

SectionKey = Literal["your_day", "before_the_bell", "earnings", "holdings", "big_read",
                     "top_3", "latest", "off_the_clock", "memes"]
LatestKey = Literal["business", "tech", "world", "pop_culture", "sports"]
LATEST_ORDER = ["business", "tech", "world", "pop_culture", "sports"]


class Link(BaseModel):
    title: str
    url: HttpUrl
    source: str                              # "WSJ", "NYT", "Reuters"...


class ChartRequest(BaseModel):
    """A chart Claude asks for; brief/charts.py fetches the numbers and draws it (EDITORIAL.md)."""
    source: Literal["kalshi", "polymarket", "bls", "yahoo"]
    id: str                                  # Kalshi event ticker, Polymarket event slug, BLS series id, Yahoo symbol
    title: str = Field(max_length=70)        # shown above the chart, e.g. "Odds for the Fed's December decision"
    view: Literal["odds", "history"] = "history"         # prediction markets: odds now, or how they moved
    transform: Literal["level", "yoy", "mom"] = "level"  # BLS: the value, % change from a year ago, monthly change
    period: Literal["1m", "3m", "6m", "1y", "2y", "5y"] = "1y"
    unit: Literal["%", ""] | None = None     # override, e.g. "%" for the unemployment rate

    @field_validator("title")
    @classmethod
    def no_numbers_in_title(cls, v):
        if re.search(r"\d+(\.\d+)?\s?%", v):
            raise ValueError("chart title can't contain a percentage; the chart shows the numbers")
        return v


# Only real, standard color emoji, one character (Wilson, Nov 27, 2026). The big emoji blocks in
# Unicode's supplementary plane, plus the common older ones that live in the BMP. No combined
# emoji (ZWJ sequences like 🧑‍💻, skin tones, flags, keycaps): some apps draw those as two
# pictures. No plain symbols (✓, ★, ↗).
EMOJI_BLOCKS = [(0x1F300, 0x1F5FF), (0x1F600, 0x1F64F), (0x1F680, 0x1F6FF), (0x1F900, 0x1F9FF), (0x1FA70, 0x1FAFF)]
EMOJI_BMP = set("☀☁☂☃☄☎☕☘☝☠☢☣☦☪☮☯☸☹☺♈♉♊♋♌♍♎♏♐♑♒♓♟♠♣♥♦♨♻♾♿⚒⚓⚔⚕⚖⚗⚙⚛⚜⚠⚡⚧⚪⚫⚰⚱⚽⚾⛄⛅⛈⛎⛏⛑⛓⛔⛩⛪⛰⛱⛲⛳⛴⛵⛷⛸⛹⛺⛽"
                "✂✅✈✉✊✋✌✍✏✒✔✖✝✡✨✳✴❄❇❌❎❓❔❕❗❣❤➕➖➗➡➰➿⌚⌛⌨⏏⏩⏪⏫⏬⏭⏮⏯⏰⏱⏲⏳⏸⏹⏺⬅⬆⬇⬛⬜⭐⭕🀄🃏")
SKIN_TONES = range(0x1F3FB, 0x1F400)


def standard_emoji(v: str) -> str:
    """One standard emoji, returned with the emoji (color) presentation selector where it needs one."""
    base = v.replace("\ufe0f", "").replace("\ufe0e", "")
    if len(base) != 1:
        raise ValueError(f"emoji must be exactly one standard emoji, got {v!r} (no combined emoji, flags or skin tones)")
    cp = ord(base)
    if cp in SKIN_TONES or not (base in EMOJI_BMP or any(lo <= cp <= hi for lo, hi in EMOJI_BLOCKS)):
        raise ValueError(f"emoji must be a standard emoji, not a symbol: {v!r}")
    # Older emoji default to a black-and-white text glyph; FE0F asks for the color emoji.
    return base + "\ufe0f" if (cp < 0x10000 or "\ufe0f" in v) else base


class Story(BaseModel):
    headline: str
    body: str                                # plain text, paragraphs split by \n\n
    link: Link
    chart: ChartRequest | None = None        # optional supporting chart (Big read, Top 3, Holdings)
    emoji: str | None = None                 # Top 3 and Off the clock: one emoji, shown before the headline

    @field_validator("emoji")
    @classmethod
    def one_emoji(cls, v):
        v = (v or "").strip()
        if not v:
            return None
        return standard_emoji(v)


class HoldingStory(Story):
    ticker: str                              # must be in config.markets.holdings

    @model_validator(mode="after")
    def headline_starts_with_ticker(self):
        if not self.headline.startswith(f"{self.ticker}: "):
            raise ValueError(f'holding headline must start with "{self.ticker}: "')
        return self


class MoverStory(BaseModel):
    ticker: str                              # must be in data.json standout.movers
    body: str                                # headline ("NVDA −6.40%") is built by code
    link: Link
    chart: ChartRequest | None = None


class OnDeck(BaseModel):
    time: str | None = None                  # "8:30", shown in the left column
    text: str


class Content(BaseModel):
    date: date
    edition: Edition
    subject: str = Field(max_length=70)
    intro: str
    section_desc: dict[SectionKey, str]
    your_day_nyc: list[Link] = Field(default=[], max_length=3)   # "NYC today"
    movers: list[MoverStory] = Field(default=[], max_length=3)
    on_deck_today: list[OnDeck] = []
    holdings_news: list[HoldingStory] = []
    big_read: Story
    top_3: list[Story] = Field(min_length=3, max_length=3)
    latest: dict[LatestKey, list[Link]]
    off_the_clock: list[Story] = Field(default=[], max_length=3)
    memes: list[HttpUrl] = Field(default=[], max_length=6)

    @field_validator("latest")
    @classmethod
    def latest_in_display_order(cls, v):
        return {k: v[k] for k in LATEST_ORDER if k in v}
