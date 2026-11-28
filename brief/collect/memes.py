"""Meme candidates, from every source in config.memes.sources (in order of preference).

- "shortsqueez": the "Memes of the Day" section of the latest Short Squeez issue
  (shortsqueez.co, daily Wall Street newsletter, posted ~4am ET on weekdays).
- "litquidity": the "Meme Cleanser" section of the latest Exec Sum issue (litquidity.co,
  read through its public WordPress feed; posted ~7am ET, so usually yesterday's issue).
- "lemmy": today's top image posts from Lemmy communities (free public API, no key).
- "reddit": Reddit API, only if access is ever approved (needs REDDIT_CLIENT_ID/SECRET).

Newsletter issues only count if they were published in the last newsletter_max_age_hours,
so the same issue never shows up two mornings in a row. Each source can fail on its own;
the block is ok: false only if every source fails. Claude looks at the candidates and picks
up to 6 (EDITORIAL.md).
"""
import html
import os
import re
from datetime import datetime, timedelta, timezone

import requests

from brief.common import TIMEOUT, USER_AGENT, get, get_json

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp")    # no GIFs (DESIGN_SYSTEM: what we drop)
# Newsletter memes are hosted on beehiiv's image CDN. Ask it for a 1008px-wide copy (2x our
# 504px column) so the email doesn't pull full-size screenshots.
BEEHIIV_FILE = re.compile(r"https://media\.beehiiv\.com/[^\"' ]*?(uploads/asset/file/[^\"'?# ]+)")
BEEHIIV_URL = "https://media.beehiiv.com/cdn-cgi/image/fit=scale-down,format=auto,quality=80,width=1008,onerror=redirect/{}"


def is_image(url: str) -> bool:
    return url.startswith("https://") and url.split("?")[0].lower().endswith(IMAGE_EXT)


# ---------- newsletters (shared) ----------

def section_images(page: str, start: str, ends: tuple[str, ...] = ()) -> list[dict]:
    """Every beehiiv image between the `start` heading and the first of `ends` (or the page end)."""
    i = page.find(start)
    if i < 0:
        return []
    stops = [j for j in (page.find(e, i) for e in ends) if j > 0]
    out, seen = [], set()
    for tag in re.findall(r"<img\b[^>]*>", page[i: min(stops, default=len(page))]):
        src = re.search(r'\bsrc="([^"]+)"', tag)
        m = BEEHIIV_FILE.search(src.group(1)) if src else None
        if not m or m.group(1) in seen or not is_image("https://x/" + m.group(1)):
            continue
        seen.add(m.group(1))
        w, h = re.search(r'\bwidth="(\d+)"', tag), re.search(r'\bheight="(\d+)"', tag)
        out.append({"url": BEEHIIV_URL.format(m.group(1)),
                    "width": int(w.group(1)) if w else None, "height": int(h.group(1)) if h else None})
    return out


def fresh(published: datetime, now: datetime, max_age_hours: float) -> bool:
    return timedelta(0) <= now - published <= timedelta(hours=max_age_hours)


def newsletter_candidates(images: list[dict], name: str, title: str, link: str) -> list[dict]:
    return [{"url": im["url"], "title": title, "community": name, "score": None, "permalink": link,
             "width": im["width"], "height": im["height"]} for im in images]


# ---------- Short Squeez ----------

def collect_shortsqueez(m: dict, now: datetime) -> list[dict]:
    home = get("https://www.shortsqueez.co/").text
    slugs = [s for s in dict.fromkeys(re.findall(r'href="(?:https://www\.shortsqueez\.co)?(/p/[a-z0-9-]+)"', home))
             if not s.startswith("/p/insiders-")]          # "Insiders" is a separate series, no memes
    out = []
    for slug in slugs[:3]:                       # newest first; only today's issue should pass
        page = get("https://www.shortsqueez.co" + slug).text
        pub = re.search(r'property="article:published_time" content="([^"]+)"', page)
        if not pub or not fresh(datetime.fromisoformat(pub.group(1).replace("Z", "+00:00")), now,
                                m["newsletter_max_age_hours"]):
            continue
        title = re.search(r'property="og:title" content="([^"]*)"', page)
        imgs = section_images(page, "Memes of the Day", ("Partner With Us", "What&#x27;d you think", "What'd you think"))
        out += newsletter_candidates(imgs, "Short Squeez", html.unescape(title.group(1)) if title else "",
                                     "https://www.shortsqueez.co" + slug)
        if out:                                  # one fresh issue a day; skip fetching the rest
            break
    return out


# ---------- Litquidity (Exec Sum) ----------

EXEC_SUM_CATEGORY = 1      # litquidity.co/wp-json/wp/v2/categories: 1 = Exec Sum, 6 = Crypto Sum


def collect_litquidity(m: dict, now: datetime) -> list[dict]:
    posts = get_json("https://litquidity.co/wp-json/wp/v2/posts",
                     params={"categories": EXEC_SUM_CATEGORY, "per_page": 3, "_fields": "link,date_gmt,title,content"})
    out = []
    for p in posts:
        published = datetime.fromisoformat(p["date_gmt"]).replace(tzinfo=timezone.utc)
        if not fresh(published, now, m["newsletter_max_age_hours"]):
            continue
        imgs = section_images(p["content"]["rendered"], "Meme Cleanser")
        out += newsletter_candidates(imgs, "Exec Sum", html.unescape(p["title"]["rendered"]), p["link"])
    return out


# ---------- Lemmy ----------

def lemmy_candidates(listing: dict, min_score: int) -> list[dict]:
    out = []
    for item in listing.get("posts", []):
        p, counts = item.get("post", {}), item.get("counts", {})
        community = item.get("community", {})
        url = p.get("url") or ""
        if p.get("nsfw") or community.get("nsfw") or p.get("removed") or p.get("deleted"):
            continue
        if p.get("featured_community") or p.get("featured_local"):     # pinned posts
            continue
        if counts.get("score", 0) < min_score or not is_image(url):
            continue
        out.append({"url": url, "title": html.unescape(p.get("name", "")),
                    "community": community.get("name", ""), "score": counts.get("score", 0),
                    "permalink": p.get("ap_id") or "", "width": None, "height": None})
    return out


def collect_lemmy(m: dict, now: datetime) -> list[dict]:
    base = f"https://{m['lemmy_instance']}/api/v3/post/list"
    per_community = [lemmy_candidates(get_json(base, params={"community_name": c, "sort": "TopDay", "limit": 50}),
                                      m["min_score"])
                     for c in m["lemmy_communities"]]
    return interleave(per_community)[: m["lemmy_candidates"]]


# ---------- Reddit ----------

def reddit_token() -> str:
    cid, secret = os.environ.get("REDDIT_CLIENT_ID"), os.environ.get("REDDIT_CLIENT_SECRET")
    if not cid or not secret:
        raise RuntimeError("REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET are not set")
    r = requests.post("https://www.reddit.com/api/v1/access_token", auth=(cid, secret),
                      data={"grant_type": "client_credentials"},
                      headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()["access_token"]


def reddit_candidates(listing: dict, min_score: int) -> list[dict]:
    out = []
    for child in listing.get("data", {}).get("children", []):
        p = child.get("data", {})
        url = p.get("url_overridden_by_dest") or p.get("url") or ""
        if p.get("over_18") or p.get("spoiler") or p.get("stickied"):
            continue
        if p.get("score", 0) < min_score or not is_image(url):
            continue
        if not url.startswith("https://i.redd.it/") and not url.startswith("https://i.imgur.com/"):
            continue
        src = ((p.get("preview") or {}).get("images") or [{}])[0].get("source") or {}
        out.append({"url": url, "title": html.unescape(p.get("title", "")), "community": p.get("subreddit"),
                    "score": p.get("score"), "permalink": "https://www.reddit.com" + p.get("permalink", ""),
                    "width": src.get("width"), "height": src.get("height")})
    return out


def collect_reddit(m: dict, now: datetime) -> list[dict]:
    headers = {"Authorization": f"bearer {reddit_token()}"}
    per_sub = [reddit_candidates(get_json(f"https://oauth.reddit.com/r/{sub}/top",
                                          params={"t": "day", "limit": 50}, headers=headers), m["reddit_min_score"])
               for sub in m["subreddits"]]
    return interleave(per_sub)[: m["lemmy_candidates"]]


# ---------- all sources ----------

SOURCES = {"shortsqueez": collect_shortsqueez, "litquidity": collect_litquidity,
           "lemmy": collect_lemmy, "reddit": collect_reddit}


def collect(cfg: dict, now: datetime) -> dict:
    m = cfg["memes"]
    candidates, errors, worked = [], [], []
    for name in m["sources"]:
        try:
            found = SOURCES[name](m, now)
        except Exception as e:                   # one broken source shouldn't sink the others
            errors.append(f"{name}: {type(e).__name__}: {e}")
            continue
        worked.append(name)
        candidates += found
    if not worked:
        raise RuntimeError("every meme source failed: " + "; ".join(errors))
    seen = set()
    candidates = [c for c in candidates if not (c["url"] in seen or seen.add(c["url"]))]
    return {"sources": worked, "source_errors": errors, "candidates": candidates}


def interleave(lists: list[list[dict]]) -> list[dict]:
    """Take the best of each feed in turn, so one big community can't fill every slot."""
    out = []
    for i in range(max((len(x) for x in lists), default=0)):
        out += [x[i] for x in lists if i < len(x)]
    return out
