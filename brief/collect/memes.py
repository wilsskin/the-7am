"""Meme candidates (Reddit API, script app, OAuth).

Top posts of the day from config.memes.subreddits: still images only, not NSFW, above a
score threshold. Returns ~12 candidates; Claude looks at them and picks 4 (EDITORIAL.md).
Without Reddit access this block is ok: false and the email skips the Meme roundup.
"""
import html
import os
from datetime import datetime

import requests

from brief.common import TIMEOUT, USER_AGENT

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API = "https://oauth.reddit.com"
IMAGE_EXT = (".jpg", ".jpeg", ".png")    # no GIFs (DESIGN_SYSTEM: what we drop)


def token() -> str:
    cid, secret = os.environ.get("REDDIT_CLIENT_ID"), os.environ.get("REDDIT_CLIENT_SECRET")
    if not cid or not secret:
        raise RuntimeError("REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET are not set")
    r = requests.post(TOKEN_URL, auth=(cid, secret), data={"grant_type": "client_credentials"},
                      headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()["access_token"]


def candidates(listing: dict, min_score: int) -> list[dict]:
    out = []
    for child in listing.get("data", {}).get("children", []):
        p = child.get("data", {})
        url = p.get("url_overridden_by_dest") or p.get("url") or ""
        if p.get("over_18") or p.get("spoiler") or p.get("stickied"):
            continue
        if p.get("score", 0) < min_score or not url.lower().endswith(IMAGE_EXT):
            continue
        if not url.startswith("https://i.redd.it/") and not url.startswith("https://i.imgur.com/"):
            continue
        src = ((p.get("preview") or {}).get("images") or [{}])[0].get("source") or {}
        out.append({"url": url, "title": html.unescape(p.get("title", "")), "subreddit": p.get("subreddit"),
                    "score": p.get("score"), "permalink": "https://www.reddit.com" + p.get("permalink", ""),
                    "width": src.get("width"), "height": src.get("height")})
    return out


def collect(cfg: dict, now: datetime) -> dict:
    m = cfg["memes"]
    headers = {"Authorization": f"bearer {token()}", "User-Agent": USER_AGENT}
    per_sub = []
    for sub in m["subreddits"]:
        r = requests.get(f"{API}/r/{sub}/top", params={"t": "day", "limit": 50}, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        per_sub.append(candidates(r.json(), m["min_score"]))
    return {"as_of": now.isoformat(), "candidates": interleave(per_sub)[: m["candidates"]]}


def interleave(lists: list[list[dict]]) -> list[dict]:
    """Take the best of each subreddit in turn, so one big sub can't fill every slot."""
    out = []
    for i in range(max((len(x) for x in lists), default=0)):
        out += [x[i] for x in lists if i < len(x)]
    return out
