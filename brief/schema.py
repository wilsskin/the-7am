"""Pydantic models for the three files a run produces (BUILD_PLAN.md §7).

data.json      written by the collectors (python -m brief.collect)
calendar.json  written by Claude from the Google Calendar connector
content.json   written by Claude: text and links only, no HTML, no markdown

Every data.json block has ok / as_of / error. A failed block keeps only those three,
and its section renders "... unavailable this morning."
"""
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
    last_close_at: datetime | None = None
    prev_close: date | None = None
    week_base: date | None = None
    year_base: date | None = None
    next_trading_day: date | None = None
    this_week: list[MarketEvent] = []
    closure_line: str | None = None          # appended to the Before the bell description


class Weather(Block):
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


class Story(BaseModel):
    headline: str
    body: str                                # plain text, paragraphs split by \n\n
    link: Link
    emoji: str | None = None                 # Top 3 and Off the clock: one emoji, shown before the headline

    @field_validator("emoji")
    @classmethod
    def one_emoji(cls, v):
        v = (v or "").strip()
        if not v:
            return None
        if len(v) > 8 or any(ch.isalnum() for ch in v):
            raise ValueError("emoji must be a single emoji")
        return v


class HoldingStory(Story):
    ticker: str                              # must be in config.markets.holdings

    @model_validator(mode="after")
    def headline_starts_with_ticker(self):
        if not self.headline.startswith(f"{self.ticker}: "):
            raise ValueError(f'holding headline must start with "{self.ticker}: "')
        return self


class StandoutStory(BaseModel):
    body: str                                # headline ("NVDA −6.40%") is built by code
    link: Link


class MoverStory(StandoutStory):
    ticker: str                              # must be in data.json standout.movers


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
    standout: StandoutStory | None = None    # old single-mover field; still read if movers is empty
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
