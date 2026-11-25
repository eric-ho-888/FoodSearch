#!/usr/bin/env python3
"""FoodSearch — find nearby food in Singapore.

A self-contained web app: Python standard library only, no API calls at runtime.
Data comes from data/eateries.json; photos are bundled in static/photos/.

    python3 app.py                 # http://localhost:8000
    python3 app.py --port 9000 --open
    python3 app.py --host 0.0.0.0  # reachable from a phone on the same network
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import mimetypes
import os
import re
import sys
import urllib.parse
import webbrowser
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:  # zoneinfo ships with 3.9+, but the tz database may be absent on slim systems
    from zoneinfo import ZoneInfo

    TZ = ZoneInfo("Asia/Singapore")
except Exception:  # pragma: no cover - fallback for machines without tzdata
    TZ = timezone(timedelta(hours=8), "SGT")

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "eateries.json"
STATIC_DIR = ROOT / "static"
PHOTO_DIR = STATIC_DIR / "photos"
MANIFEST_FILE = PHOTO_DIR / "manifest.json"

CATEGORIES = ["Chinese", "Malay", "Indian", "Western", "Japanese", "Korean", "Others"]

# Singapore's planning regions, in the URA order used across the island.
REGIONS = ["Central", "North", "North-East", "East", "West"]
DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_ABBR = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

POPULAR_SEARCHES = [
    "satay", "mee rebus", "mee siam", "nasi lemak", "laksa",
    "chicken rice", "char kway teow", "dim sum", "ramen",
    "chilli crab", "roti prata", "biryani", "bibimbap", "truffle fries",
]

# Query spellings / colloquial names mapped onto the words used in the data.
SYNONYMS = [
    ("char kuay teow", "char kway teow"),
    ("kway tiao", "kway teow"),
    ("kuay teow", "kway teow"),
    ("mee pok", "bak chor mee"),
    ("mi pok", "bak chor mee"),
    ("mi rebus", "mee rebus"),
    ("mi siam", "mee siam"),
    ("mi goreng", "mee goreng"),
    ("otak otak", "otah"),
    ("nasilemak", "nasi lemak"),
    ("bakuteh", "bak kut teh"),
    ("dimsum", "dim sum"),
    ("dosa", "thosai"),
    ("sate", "satay"),
    ("lamian", "ramen"),
]

MAX_QUERY_LEN = 120


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_json(path: Path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"warning: could not read {path}: {exc}", file=sys.stderr)
        return default


_RAW = _load_json(DATA_FILE, {})
META = _RAW.get("meta", {}) if isinstance(_RAW, dict) else {}
EATERIES = [e for e in _RAW.get("eateries", []) if isinstance(e, dict) and e.get("id")] if isinstance(_RAW, dict) else []
BY_ID = {e["id"]: e for e in EATERIES}
MANIFEST = _load_json(MANIFEST_FILE, {}) if MANIFEST_FILE.exists() else {}
if not isinstance(MANIFEST, dict):
    MANIFEST = {}

CITY = META.get("city", "Singapore")
NOTE = META.get(
    "note",
    "Demo dataset. Listings, operating hours and reviews are illustrative samples "
    "for demonstration purposes — confirm details before visiting.",
)
DEFAULT_CENTER = META.get("default_center", {"lat": 1.29027, "lng": 103.851959, "label": "Singapore city centre"})

# A listing may name its region explicitly; otherwise derive it from the area.
AREA_REGIONS = {
    "changi": "East", "katong": "East", "east coast": "East", "geylang": "East",
    "old airport": "East", "bedok": "East", "tampines": "East", "pasir ris": "East",
    "yishun": "North", "sembawang": "North", "woodlands": "North", "admiralty": "North",
    "marsiling": "North", "chong pang": "North",
    "serangoon": "North-East", "kovan": "North-East", "hougang": "North-East",
    "punggol": "North-East", "sengkang": "North-East", "ang mo kio": "North-East",
    "jurong": "West", "boon lay": "West", "taman jurong": "West", "bukit timah": "West",
    "clementi": "West", "bukit batok": "West", "chua chu kang": "West",
}


def region_of(eatery: dict) -> str:
    """The listing's region: explicit `region`, else inferred from `area`, else Central."""
    explicit = str(eatery.get("region") or "").strip()
    if explicit in REGIONS:
        return explicit
    area = str(eatery.get("area") or "").lower()
    for needle, region in AREA_REGIONS.items():
        if needle in area:
            return region
    return "Central"


HAYSTACK: dict[str, list[str]] = {}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _singular(token: str) -> str:
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _build_haystacks() -> None:
    for e in EATERIES:
        parts = [
            e.get("name", ""), e.get("category", ""), e.get("area", ""),
            e.get("description", ""),
            " ".join(e.get("specialties", [])),
            " ".join(e.get("photo_queries", [])),
        ]
        HAYSTACK[e["id"]] = [_singular(t) for t in _tokenize(" ".join(parts))]


_build_haystacks()


def photos_for(eatery_id: str) -> list[dict]:
    """Return up to two bundled photos, each with Commons attribution."""
    photos: list[dict] = []
    for entry in MANIFEST.get(eatery_id, []):
        name = entry.get("file")
        if not name or len(photos) >= 2:
            continue
        if (PHOTO_DIR / name).is_file():
            photo = dict(entry)
            photo["src"] = "/static/photos/" + urllib.parse.quote(name)
            photos.append(photo)
    if not photos:  # manifest gap — fall back to files on disk
        for idx in (1, 2):
            for ext in (".webp", ".jpg", ".jpeg", ".png"):
                candidate = PHOTO_DIR / f"{eatery_id}-{idx}{ext}"
                if candidate.is_file():
                    photos.append({
                        "file": candidate.name,
                        "src": "/static/photos/" + urllib.parse.quote(candidate.name),
                        "article": "",
                        "title": candidate.name,
                        "source": "",
                        "artist": "Unknown",
                        "license": "See Wikimedia Commons",
                        "license_url": "",
                    })
                    break
    return photos


# ---------------------------------------------------------------------------
# Hours
# ---------------------------------------------------------------------------

def _minutes(hhmm: str) -> int:
    try:
        h, m = hhmm.split(":")
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return 0


def fmt_time(hhmm: str) -> str:
    """'19:30' -> '7:30 pm'."""
    total = _minutes(hhmm) % (24 * 60)
    h, m = divmod(total, 60)
    suffix = "am" if h < 12 else "pm"
    return f"{h % 12 or 12}:{m:02d} {suffix}"


def _ranges(eatery: dict, day_index: int) -> list[tuple[int, int]]:
    raw = eatery.get("hours", {}).get(DAY_KEYS[day_index % 7], []) or []
    out = []
    for pair in raw:
        if isinstance(pair, (list, tuple)) and len(pair) >= 2:
            out.append((_minutes(pair[0]), _minutes(pair[1])))
    return out


def _next_start(eatery: dict, day: int, mins: int):
    """Find the next opening time at or after `mins` on `day`.

    Returns (weekday_offset, start_minutes) or None.
    """
    for offset in range(0, 8):
        di = day + offset
        for start, _end in _ranges(eatery, di):
            if offset == 0 and start <= mins:
                continue
            return offset, start
    return None


def opening_state(eatery: dict, now: datetime) -> dict:
    """Open/closed status plus a human-readable next transition."""
    day = now.weekday()
    mins = now.hour * 60 + now.minute

    for start, end in _ranges(eatery, day):
        end_abs = end if end > start else end + 24 * 60
        if start <= mins < end_abs:
            close_hhmm = f"{end_abs % (24 * 60) // 60:02d}:{end_abs % 60:02d}"
            return {
                "open": True,
                "status": "Open",
                "detail": f"closes {fmt_time(close_hhmm)}",
                "today": _today_text(eatery, day),
            }

    # An overnight slot from yesterday, e.g. 11:00–02:00.
    for start, end in _ranges(eatery, day - 1):
        if end <= start and mins < end:
            return {
                "open": True,
                "status": "Open",
                "detail": f"closes {fmt_time(f'{end // 60:02d}:{end % 60:02d}')}",
                "today": _today_text(eatery, day),
            }

    nxt = _next_start(eatery, day, mins)
    if nxt:
        offset, start = nxt
        start_text = fmt_time(f"{start // 60:02d}:{start % 60:02d}")
        if offset == 0:
            detail = f"opens {start_text}"
        elif offset == 1:
            detail = f"opens {start_text} tomorrow"
        else:
            detail = f"opens {start_text} {DAY_ABBR[(day + offset) % 7]}"
        status = "Closed"
    else:
        detail = "no opening hours listed"
        status = "Closed"

    return {"open": False, "status": status, "detail": detail, "today": _today_text(eatery, day)}


def _today_text(eatery: dict, day: int) -> str:
    ranges = _ranges(eatery, day)
    if not ranges:
        return "Closed today"
    formatted = []
    for start, end in ranges:
        start_hhmm = f"{start // 60:02d}:{start % 60:02d}"
        end_hhmm = f"{end // 60:02d}:{end % 60:02d}"
        formatted.append(f"{fmt_time(start_hhmm)} – {fmt_time(end_hhmm)}")
    return " · ".join(formatted)


def week_hours(eatery: dict, now: datetime) -> list[dict]:
    today = now.weekday()
    rows = []
    for idx, key in enumerate(DAY_KEYS):
        ranges = eatery.get("hours", {}).get(key, []) or []
        if not ranges:
            text = "Closed"
        else:
            bits = []
            for pair in ranges:
                if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                    bits.append(f"{fmt_time(pair[0])} – {fmt_time(pair[1])}")
            text = " · ".join(bits) or "Closed"
        rows.append({"day": DAY_NAMES[idx], "text": text, "today": idx == today})
    return rows


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def normalize_query(query: str) -> str:
    text = " " + " ".join(_tokenize(query[:MAX_QUERY_LEN])) + " "
    for old, new in SYNONYMS:
        text = text.replace(f" {old} ", f" {new} ")
    return " ".join(text.split())


def _token_matches(needle: str, hay: list[str]) -> bool:
    needle = _singular(needle)
    for token in hay:
        token = _singular(token)
        if token == needle:
            return True
        if len(needle) >= 3 and token.startswith(needle):
            return True
    return False


def _query_tokens(norm_query: str) -> list[str]:
    seen = []
    for token in norm_query.split():
        token = _singular(token)
        if token and token not in seen:
            seen.append(token)
    return seen


def edit_distance(a: str, b: str, limit: int = 1) -> int:
    """Optimal-string-alignment distance (edits + adjacent swaps), with early bail-out."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev2: list[int] = []
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        best = i
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            value = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
            if i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                value = min(value, prev2[j - 2] + 1)  # transposition, e.g. "chciken"
            current.append(value)
            best = min(best, value)
        if best > limit:
            return limit + 1
        prev2, previous = previous, current
    return previous[-1]


def _token_matches_fuzzy(needle: str, hay: list[str]) -> bool:
    """Typo-tolerant match: allow one edit on words of four letters or more."""
    if _token_matches(needle, hay):
        return True
    if len(needle) < 4:
        return False
    # Longer words tolerate a second edit ("bimbap" -> "bibimbap").
    allowance = 2 if len(needle) >= 6 else 1
    for token in hay:
        if len(token) >= 4 and edit_distance(needle, token, allowance) <= allowance:
            return True
    return False


def _score(eatery: dict, norm_query: str, tokens: list[str], fuzzy: bool = False) -> tuple[float, list[str], int]:
    """Score one eatery. Returns (score, matched specialties, tokens hit)."""
    match = _token_matches_fuzzy if fuzzy else _token_matches
    hay = HAYSTACK.get(eatery["id"], [])
    name_hay = [_singular(t) for t in _tokenize(eatery.get("name", ""))]
    category_hay = [_singular(t) for t in _tokenize(eatery.get("category", ""))]
    area_hay = [_singular(t) for t in _tokenize(eatery.get("area", ""))]
    desc_hay = [_singular(t) for t in _tokenize(eatery.get("description", ""))]
    photo_hay = [_singular(t) for t in _tokenize(" ".join(eatery.get("photo_queries", [])))]

    score = 0.0
    matched: list[str] = []
    hits = 0

    for token in tokens:
        if match(token, hay):
            hits += 1
        for hay_list, weight in (
            (name_hay, 18), (category_hay, 12), (area_hay, 8),
            (desc_hay, 2), (photo_hay, 1),
        ):
            if match(token, hay_list):
                score += weight
                if hay_list is name_hay and len(token) >= 3:
                    break

    name_lower = eatery.get("name", "").lower()
    if norm_query and norm_query in name_lower:
        score += 40

    for specialty in eatery.get("specialties", []):
        spec_tokens = [_singular(t) for t in _tokenize(specialty)]
        if norm_query and norm_query and norm_query in specialty.lower():
            score += 22
            matched.append(specialty)
        elif tokens and all(match(t, spec_tokens) for t in tokens):
            score += 16
            matched.append(specialty)
        else:
            partial = sum(1 for t in tokens if match(t, spec_tokens))
            score += 3 * partial

    try:
        score += float(eatery.get("rating", 0)) * 1.5
        score += min(int(eatery.get("review_count", 0)), 5000) / 1500
    except (TypeError, ValueError):
        pass

    return score, matched, hits


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def distance_label(km: float) -> str:
    if km < 0.05:
        return "right here"
    if km < 1:
        metres = int(round(km * 1000 / 10.0) * 10)
        return f"{metres} m away"
    return f"{km:.1f} km away"


def _parse_coords(params: dict) -> tuple[float, float] | None:
    try:
        lat = float(params.get("lat", ""))
        lng = float(params.get("lng", ""))
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    return lat, lng


def search_eateries(params: dict, now: datetime | None = None) -> dict:
    now = now or datetime.now(TZ)
    query_raw = (params.get("q") or "").strip()[:MAX_QUERY_LEN]
    category = (params.get("category") or "All").strip()
    if category not in CATEGORIES:
        category = "All"
    region = (params.get("region") or "All").strip()
    if region.title() in REGIONS:
        region = region.title()
    elif region != "All":
        region = "All"
    sort = (params.get("sort") or "relevance").strip()
    if sort not in ("relevance", "distance", "rating"):
        sort = "relevance"
    open_only = str(params.get("open", "")).lower() in ("1", "true", "yes", "on")
    origin = _parse_coords(params)

    # "Nearest" without a location still sorts sensibly, from the city centre.
    sort_origin = origin
    if sort == "distance" and not sort_origin:
        sort_origin = (DEFAULT_CENTER["lat"], DEFAULT_CENTER["lng"])

    norm_query = normalize_query(query_raw)
    tokens = _query_tokens(norm_query)

    pool = [
        e for e in EATERIES
        if (category == "All" or e.get("category") == category)
        and (region == "All" or region_of(e) == region)
    ]
    scored = []
    relaxed = False

    for eatery in pool:
        score, matched, hits = _score(eatery, norm_query, tokens)
        if tokens and hits < len(tokens):
            continue
        scored.append((eatery, score, matched))

    if tokens and not scored:
        for eatery in pool:
            score, matched, hits = _score(eatery, norm_query, tokens, fuzzy=True)
            if hits:
                scored.append((eatery, score, matched))
        relaxed = bool(scored)

    items = []
    for eatery, score, matched in scored:
        state = opening_state(eatery, now)
        if open_only and not state["open"]:
            continue
        items.append((eatery, score, matched))

    if sort == "distance":
        def key(item):
            eatery = item[0]
            dist = haversine_km(sort_origin[0], sort_origin[1], eatery.get("lat", 0), eatery.get("lng", 0))
            return (dist, -float(eatery.get("rating", 0) or 0))
    elif sort == "rating":
        def key(item):
            eatery = item[0]
            return (-float(eatery.get("rating", 0) or 0), -int(eatery.get("review_count", 0) or 0),
                    eatery.get("name", ""))
    else:
        def key(item):
            eatery = item[0]
            open_now = opening_state(eatery, now)["open"]
            return (-item[1], not open_now, -float(eatery.get("rating", 0) or 0),
                    -int(eatery.get("review_count", 0) or 0))

    items.sort(key=key)

    display_origin = origin or (sort_origin if sort == "distance" else None)
    results = [public_eatery(e, now, origin=display_origin, matched=matched, query=norm_query)
               for e, _score_value, matched in items]

    return {
        "results": results,
        "relaxed": relaxed,
        "count": len(results),
        "query": query_raw,
        "category": category,
        "region": region,
        "sort": sort,
        "open_only": open_only,
        "now": now,
        "origin": origin,
        "display_origin": display_origin,
        "sort_origin": sort_origin,
    }


def _top_reviews(eatery: dict) -> list[dict]:
    reviews = [r for r in eatery.get("reviews", []) if isinstance(r, dict)]
    reviews = sorted(reviews, key=lambda r: str(r.get("date", "")), reverse=True)
    reviews.sort(key=lambda r: float(r.get("rating", 0) or 0), reverse=True)
    out = []
    for review in reviews:
        item = dict(review)
        item["date_display"] = pretty_date(str(review.get("date", "")))
        out.append(item)
    return out


def pretty_date(iso_date: str) -> str:
    try:
        dt = datetime.strptime(iso_date, "%Y-%m-%d")
        return f"{dt.day} {dt.strftime('%b %Y')}"
    except ValueError:
        return iso_date


def public_eatery(eatery: dict, now: datetime, origin=None, matched=None, query="") -> dict:
    state = opening_state(eatery, now)
    reviews = _top_reviews(eatery)
    photos = photos_for(eatery["id"])
    specialties = list(eatery.get("specialties", []))
    matched = [m for m in (matched or []) if m in specialties]
    if not matched and not query:
        matched = []
    for specialty in specialties:  # dedupe while keeping data order
        if specialty not in matched and query and query in specialty.lower():
            matched.append(specialty)

    distance_km = None
    distance_text = None
    if origin:
        distance_km = haversine_km(origin[0], origin[1], eatery.get("lat", 0), eatery.get("lng", 0))
        distance_text = distance_label(distance_km)

    return {
        "id": eatery["id"],
        "name": eatery.get("name", ""),
        "category": eatery.get("category", ""),
        "region": region_of(eatery),
        "area": eatery.get("area", ""),
        "address": eatery.get("address", ""),
        "description": eatery.get("description", ""),
        "price": eatery.get("price", ""),
        "rating": float(eatery.get("rating", 0) or 0),
        "review_count": int(eatery.get("review_count", 0) or 0),
        "verified": bool(eatery.get("verified", True)),
        "specialties": specialties,
        "matched_specialties": matched[:3],
        "chips": card_chips(specialties, matched),
        "photos": photos,
        "open": state,
        "hours_today": state["today"],
        "distance_km": round(distance_km, 3) if distance_km is not None else None,
        "distance_label": distance_text,
        "top_review": reviews[0] if reviews else None,
        "reviews": reviews,
        "maps_url": "https://www.google.com/maps/search/?api=1&query="
                    + urllib.parse.quote(f"{eatery.get('name', '')} {eatery.get('address', '')}".strip()),
    }


def card_chips(specialties: list[str], matched: list[str]) -> list[str]:
    chips: list[str] = []
    for item in list(matched) + specialties:
        if item not in chips:
            chips.append(item)
        if len(chips) >= 4:
            break
    return chips


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

def esc(value) -> str:
    return html.escape(str(value), quote=True)


def brand() -> str:
    """The wordmark plus its small, colourful tagline."""
    return (
        '<a class="brand" href="/">'
        '<span class="brand-name">Food<span class="brand-accent">Search</span></span>'
        '<span class="brand-tagline">yummy food nearby</span>'
        '</a>'
    )


FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
    "%3Crect width='64' height='64' rx='14' fill='%23c0392b'/%3E"
    "%3Ctext x='32' y='45' font-family='Georgia,serif' font-size='36' fill='%23fff' "
    "text-anchor='middle'%3EF%3C/text%3E%3C/svg%3E"
)


def asset_version() -> str:
    """Short content hash of the CSS/JS, used to bust browser caches on deploy."""
    digest = hashlib.sha256()
    for name in ("app.css", "app.js"):
        try:
            digest.update((STATIC_DIR / name).read_bytes())
        except OSError:
            digest.update(name.encode())
    return digest.hexdigest()[:10]


ASSET_VERSION = asset_version()


def page(title: str, body: str) -> bytes:
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="FoodSearch — find nearby Chinese, Malay, Indian, Western, Japanese, Korean and other food in Singapore.">
<link rel="icon" href="{FAVICON}">
<link rel="stylesheet" href="/static/app.css?v={ASSET_VERSION}">
</head>
<body>
{body}
<script src="/static/app.js?v={ASSET_VERSION}" defer></script>
</body>
</html>
"""
    return doc.encode("utf-8")


def stars(rating: float) -> str:
    full = max(0, min(5, int(round(rating))))
    return "★" * full + "☆" * (5 - full)


def category_options(active: str, keep: dict | None = None) -> str:
    """Cuisine chips. `keep` carries the current query/filters across clicks."""
    out = []
    active = active if active in CATEGORIES else "All"
    keep = dict(keep or {})
    for name in ["All"] + CATEGORIES:
        classes = "chip chip-cat" + (" is-active" if name == active else "")
        dot = "" if name == "All" else f'<span class="cat-dot cat-{name.lower()}"></span>'
        label = "All" if name == "All" else name
        target = dict(keep)
        target["category"] = name
        out.append(
            f'<a class="{classes}" href="{esc(index_url(**target))}" '
            f'data-category="{esc(name)}">{dot}{esc(label)}</a>'
        )
    return "\n".join(out)


def index_url(**overrides) -> str:
    params = {}
    for key in ("q", "category", "region", "sort", "open", "lat", "lng"):
        if key in overrides:
            value = overrides[key]
            if value not in (None, "", "All", "relevance", 0, False):
                params[key] = value
    query = urllib.parse.urlencode(params)
    return "/" + (f"?{query}" if query else "")


def render_card(item: dict) -> str:
    photos = item["photos"]
    photo = photos[0] if photos else None
    if photo:
        alt = f"{item['name']} — {photo.get('article') or 'food photo'}"
        media = (f'<img src="{esc(photo["src"])}" alt="{esc(alt)}" loading="lazy" '
                 f'width="640" height="400">')
        count = (f'<span class="badge badge-photos">2 photos</span>'
                 if len(photos) > 1 else "")
    else:
        media = '<div class="photo-placeholder" aria-hidden="true">No photo</div>'
        count = ""

    chips = "".join(
        f'<li class="chip{" chip-match" if chip in item["matched_specialties"] else ""}">'
        f'{esc(chip)}</li>'
        for chip in item["chips"]
    )
    verified_note = "" if item["verified"] else (
        '<p class="unverified" title="The exact outlet at this address is not confirmed">'
        "Indicative listing</p>"
    )
    chips_html = f'<ul class="chips" aria-label="Specialties">{chips}</ul>' if chips else ""

    meta_bits = [item["region"] + " region", item["area"], item["price"]]
    if item["distance_label"]:
        meta_bits.append(item["distance_label"])
    meta_text = " · ".join(esc(bit) for bit in meta_bits if bit)

    review = item["top_review"]
    if review:
        review_html = (
            '<blockquote class="quote">'
            f'<p>“{esc(review.get("text", ""))}”</p>'
            f'<cite>— {esc(review.get("author", "Anonymous"))}</cite>'
            "</blockquote>"
        )
    else:
        review_html = ""

    open_class = "is-open" if item["open"]["open"] else "is-closed"
    href = f'/eatery/{esc(item["id"])}'

    return f"""
<article class="card">
  <a class="card-media" href="{href}" tabindex="-1" aria-hidden="true">
    {media}
    <span class="badge badge-category cat-{esc(item["category"].lower())}">{esc(item["category"])}</span>
    <span class="badge badge-rating" title="Average rating">★ {item["rating"]:.1f}</span>
    {count}
  </a>
  <div class="card-body">
    <h3 class="card-title"><a href="{href}">{esc(item["name"])}</a></h3>
    {verified_note}
    <p class="card-meta">{meta_text}</p>
    <p class="status {open_class}"><span class="dot"></span>{esc(item["open"]["status"])} · {esc(item["open"]["detail"])}</p>
    {chips_html}
    {review_html}
  </div>
</article>"""


def render_empty(query: str, region: str = "All", category: str = "All") -> str:
    where = []
    if query:
        where.append(f"“{esc(query)}”")
    if category != "All":
        where.append(f"in {esc(category)}")
    if region != "All":
        where.append(f"in the {esc(region)} region")
    if where:
        title = "No places match " + " ".join(where)
    else:
        title = "No places match these filters"

    hint = ('<p>Try a dish name like <em>satay</em>, <em>mee rebus</em> or '
            '<em>nasi lemak</em>, or clear your filters.</p>')
    if query and region != "All":
        elsewhere = search_eateries({"q": query, "category": category})
        if elsewhere["count"]:
            names = ", ".join(r["name"] for r in elsewhere["results"][:3])
            more = " and more" if elsewhere["count"] > 3 else ""
            hint = (f'<p><strong>{esc(query)}</strong> is available elsewhere: '
                    f'{esc(names)}{more}.</p>')
            return f"""
<div class="empty">
  <p class="empty-icon" aria-hidden="true">🥢</p>
  <h3>{title}</h3>
  {hint}
  <a class="btn-primary" href="{esc(index_url(q=query, category=category))}">Search all regions</a>
</div>"""

    return f"""
<div class="empty">
  <p class="empty-icon" aria-hidden="true">🥢</p>
  <h3>{title}</h3>
  {hint}
  <a class="btn-primary" href="/">Clear search</a>
</div>"""


def region_tabs(active: str, counts: dict, keep: dict) -> str:
    """Singapore region tabs, rendered directly in front of the "Near me" button."""
    active = active if active in REGIONS else "All"
    out = []
    for name in ["All"] + REGIONS:
        target = dict(keep)
        target["region"] = name
        classes = "region-tab" + (" is-active" if name == active else "")
        label = "All" if name == "All" else name
        badge = counts.get(name, 0)
        pressed = "true" if name == active else "false"
        title = "All regions" if name == "All" else f"{name} region"
        out.append(
            f'<a class="{classes}" href="{esc(index_url(**target))}" '
            f'data-region="{esc(name)}" role="tab" aria-selected="{pressed}" '
            f'title="{esc(title)}">'
            f'<span class="region-name">{esc(label)}</span>'
            f'<span class="region-count">{badge}</span></a>'
        )
    return "\n".join(out)


def toolbar(count: int, query: str, category: str, region: str, sort: str, open_only: bool,
            relaxed: bool, located: bool, region_counts: dict, keep: dict) -> str:
    count_text = f"{count} place{'s' if count != 1 else ''}"
    if query:
        count_text += f" for “{query}”"
    if category != "All":
        count_text += f" · {category}"
    if region != "All":
        count_text += f" · {region} region"
    if located:
        count_text += " · sorted by distance from you"
    elif sort == "distance":
        count_text += " · nearest first (from the city centre)"

    options = "".join(
        f'<option value="{value}"{" selected" if sort == value else ""}>{label}</option>'
        for value, label in (
            ("relevance", "Best match"), ("distance", "Nearest"), ("rating", "Top rated"),
        )
    )
    banner = ""
    if relaxed:
        banner = ('<p class="banner" role="status">No exact matches — showing the closest '
                  'results instead.</p>')

    return f"""
<div class="toolbar">
  <div class="toolbar-head">
    <h2 class="section-title">Places to eat</h2>
    <p class="result-count" id="result-count" aria-live="polite">{esc(count_text)}</p>
  </div>
  <div class="controls">
    <nav class="region-tabs" id="region-tabs" aria-label="Singapore regions" role="tablist">
      {region_tabs(region, region_counts, keep)}
    </nav>
    <button type="button" class="btn-ghost" id="locate-btn">Near me</button>
    <label class="switch">
      <input type="checkbox" id="open-toggle"{' checked' if open_only else ''}>
      <span>Open now</span>
    </label>
    <label class="select-wrap">
      <span class="sr-only">Sort by</span>
      <select id="sort">{options}</select>
    </label>
  </div>
</div>
{banner}"""


def render_index(params: dict, now: datetime) -> bytes:
    outcome = search_eateries(params, now)
    results = outcome["results"]
    query = outcome["query"]
    category = outcome["category"]
    region = outcome["region"]
    sort = outcome["sort"]
    open_only = outcome["open_only"]
    origin = outcome["origin"]
    # Distances only appear for a real (non-default) location; "Nearest" without
    # one still orders results around the city centre, quietly.
    located = bool(origin) and origin != (DEFAULT_CENTER["lat"], DEFAULT_CENTER["lng"])
    if not located:
        for result in results:
            result["distance_km"] = result["distance_label"] = None

    suggestions = " ".join(
        f'<a class="suggestion" href="{esc(index_url(q=term))}" data-q="{esc(term)}">{esc(term)}</a>'
        for term in POPULAR_SEARCHES
    )

    # Hidden inputs keep sort/open/location when the form submits without JS.
    hidden = {
        "category": category if category != "All" else "",
        "region": region if region != "All" else "",
        "sort": sort if sort != "relevance" else "",
        "open": "1" if open_only else "",
        "lat": origin[0] if origin else "",
        "lng": origin[1] if origin else "",
    }
    form_state_inputs = "".join(
        f'<input type="hidden" name="{name}" value="{esc(value)}">'
        for name, value in hidden.items() if value != ""
    )

    cards = ("".join(render_card(item) for item in results) if results
             else render_empty(query, region, category))
    count = len(results)

    # Tab counts reflect the current query/category/open filter, ignoring region
    # itself, so each tab shows how much food is actually there.
    region_counts = {"All": 0}
    scoped = search_eateries({**params, "region": "All"}, now)
    for item in scoped["results"]:
        result_region = item["region"]
        region_counts[result_region] = region_counts.get(result_region, 0) + 1
        region_counts["All"] += 1

    tab_keep = {"q": query, "category": category, "sort": sort,
                "open": "1" if open_only else "",
                "lat": origin[0] if origin else "", "lng": origin[1] if origin else ""}

    body = f"""
<div id="app"
     data-q="{esc(query)}"
     data-category="{esc(category)}"
     data-region="{esc(region)}"
     data-sort="{esc(sort)}"
     data-open="{'1' if open_only else '0'}"
     data-lat="{esc(origin[0]) if origin else ''}"
     data-lng="{esc(origin[1]) if origin else ''}">
<header class="site-header">
  <div class="wrap header-top">
    {brand()}
    <p class="header-note"><span class="live-dot"></span>{esc(CITY)} · {esc(fmt_clock(now))} SGT</p>
  </div>
  <div class="wrap">
    <form class="searchbar" id="search-form" action="/" method="get" role="search">
      <svg class="search-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><path d="m20 20-4.2-4.2"></path></svg>
      <input id="q" name="q" type="search" value="{esc(query)}"
             placeholder="Search a dish — satay, mee rebus, nasi lemak…"
             autocomplete="off" aria-label="Search for food or a dish">
      <button type="submit" class="btn-primary">Search</button>
      {form_state_inputs}
    </form>
    <nav class="chiprow" aria-label="Cuisine categories">
      {category_options(category, keep={"q": query, "region": region, "sort": sort,
                                       "open": "1" if open_only else "",
                                       "lat": origin[0] if origin else "",
                                       "lng": origin[1] if origin else ""})}
    </nav>
    <div class="suggestions"><span>Popular:</span>{suggestions}</div>
  </div>
</header>

<main class="wrap main">
  {toolbar(count, query, category, region, sort, open_only, outcome["relaxed"], located,
           region_counts, tab_keep)}
  <div class="grid" id="results" aria-live="polite" aria-busy="false">
    {cards}
  </div>
</main>

<footer class="site-footer">
  <div class="wrap footer-inner">
    <p><strong>FoodSearch</strong> · {esc(CITY)}</p>
    <p>{esc(NOTE)} Photos via Wikimedia Commons (credited per listing).</p>
  </div>
</footer>
</div>
"""
    return page("FoodSearch — nearby food in Singapore", body)


def fmt_clock(now: datetime) -> str:
    h = now.hour
    suffix = "am" if h < 12 else "pm"
    return f"{h % 12 or 12}:{now.minute:02d} {suffix}"


def render_photo_figure(photo: dict, name: str) -> str:
    credit_bits = []
    if photo.get("artist") and photo["artist"] != "Unknown":
        credit_bits.append(esc(photo["artist"]))
    if photo.get("license"):
        credit_bits.append(esc(photo["license"]))
    credit = " · ".join(credit_bits)
    if photo.get("source"):
        credit = f'<a href="{esc(photo["source"])}" target="_blank" rel="noopener noreferrer">{credit}</a>'
    caption = photo.get("article") or "Dish photo"
    alt = f"{name} — {caption}"
    return f"""
  <figure class="photo">
    <img src="{esc(photo["src"])}" alt="{esc(alt)}" loading="lazy" width="900" height="675">
    <figcaption>{esc(caption)}{f" · {credit}" if credit else ""}</figcaption>
  </figure>"""


def render_review(review: dict) -> str:
    author = review.get("author", "Anonymous")
    initials = "".join(part[0] for part in author.replace(".", " ").split() if part)[:2].upper() or "?"
    rating = float(review.get("rating", 0) or 0)
    return f"""
<article class="review">
  <header class="review-head">
    <span class="avatar" aria-hidden="true">{esc(initials)}</span>
    <div>
      <p class="review-author">{esc(author)}</p>
      <p class="review-date">{esc(review.get("date_display", review.get("date", "")))}</p>
    </div>
  </header>
  <p class="review-stars" aria-label="Rated {rating:g} out of 5">{stars(rating)} <span>{rating:.1f}</span></p>
  <p class="review-text">{esc(review.get("text", ""))}</p>
</article>"""


def render_detail(eatery_id: str, now: datetime) -> bytes | None:
    eatery = BY_ID.get(eatery_id)
    if not eatery:
        return None
    state = opening_state(eatery, now)
    item = public_eatery(eatery, now)
    photos = item["photos"]
    gallery = "".join(render_photo_figure(photo, item["name"]) for photo in photos) or (
        '<p class="muted">No photos are available for this listing.</p>'
    )
    chips = "".join(f'<li class="chip">{esc(spec)}</li>' for spec in item["specialties"])
    hours_rows = "".join(
        "<tr{}><th scope=\"row\">{}{}</th><td>{}</td></tr>".format(
            ' class="is-today"' if row["today"] else "",
            esc(row["day"]),
            " (today)" if row["today"] else "",
            esc(row["text"]),
        )
        for row in week_hours(eatery, now)
    )
    reviews = item["reviews"]
    review_html = "".join(render_review(review) for review in reviews) or (
        '<p class="muted">No reviews yet.</p>'
    )
    open_class = "is-open" if state["open"] else "is-closed"

    body = f"""
<header class="site-header detail-header">
  <div class="wrap header-top">
    {brand()}
    <a class="back-link" href="/">← Back to search</a>
  </div>
</header>

<main class="wrap detail">
  <nav class="crumbs" aria-label="Breadcrumb">
    <a href="/">Home</a> <span aria-hidden="true">/</span>
    <a href="{esc(index_url(category=item["category"]))}">{esc(item["category"])}</a> <span aria-hidden="true">/</span>
    <a href="{esc(index_url(region=item["region"]))}">{esc(item["region"])}</a> <span aria-hidden="true">/</span>
    <span aria-current="page">{esc(item["name"])}</span>
  </nav>

  <section class="detail-hero">
    <div class="detail-hero-text">
      <p class="badge badge-category cat-{esc(item["category"].lower())}">{esc(item["category"])}</p>
      <h1>{esc(item["name"])}</h1>
      <p class="detail-meta">
        <span>{esc(item["area"])}</span><span aria-hidden="true">·</span>
        <span>{esc(item["price"])}</span><span aria-hidden="true">·</span>
        <span class="rating"><span aria-hidden="true">★</span> {item["rating"]:.1f}
          <span class="muted">({item["review_count"]:,} reviews)</span></span>
      </p>
      <p class="status {open_class}"><span class="dot"></span>{esc(state["status"])} · {esc(state["detail"])}</p>
      <p class="address">{esc(item["address"])}</p>
      <div class="hero-actions">
        <a class="btn-primary" href="{esc(item["maps_url"])}" target="_blank" rel="noopener noreferrer">Open in Maps</a>
        <a class="btn-ghost" href="{esc(index_url(q=item["specialties"][0] if item["specialties"] else item["name"]))}">Find similar</a>
      </div>
    </div>
    <div class="gallery">{gallery}</div>
  </section>

  <div class="detail-columns">
    <section class="panel">
      <h2>About</h2>
      <p class="lede">{esc(item["description"])}</p>
      {"" if item["verified"] else (
        '<p class="unverified-note">This is an <strong>indicative listing</strong>: the venue is a '
        'real location, but the exact outlet, hours and reviews shown are illustrative and not confirmed.</p>'
      )}
      <h3>Specialties</h3>
      <ul class="chips chips-lg">{chips}</ul>
    </section>

    <section class="panel hours-panel">
      <h2>Opening hours</h2>
      <p class="status {open_class}"><span class="dot"></span>{esc(state["status"])} · {esc(state["detail"])}</p>
      <table class="hours">
        <caption class="sr-only">Weekly opening hours for {esc(item["name"])}</caption>
        <tbody>{hours_rows}</tbody>
      </table>
      <p class="muted small">Times shown in Singapore time (SGT).</p>
    </section>
  </div>

  <section class="reviews-section">
    <div class="section-head">
      <h2>Top reviews</h2>
      <p class="muted">Highest rated and most recent</p>
    </div>
    <div class="review-grid">{review_html}</div>
  </section>

  <p class="disclaimer">{esc(NOTE)}</p>
</main>

<footer class="site-footer">
  <div class="wrap footer-inner">
    <p><strong>FoodSearch</strong> · {esc(CITY)}</p>
    <p>Photos via Wikimedia Commons, credited above.</p>
  </div>
</footer>
"""
    return page(f'{item["name"]} — FoodSearch', body)


def render_404(message: str = "That page does not exist.") -> bytes:
    body = f"""
<header class="site-header">
  <div class="wrap header-top">
    {brand()}
  </div>
</header>
<main class="wrap detail">
  <div class="empty">
    <p class="empty-icon" aria-hidden="true">🍽️</p>
    <h1>Not found</h1>
    <p>{esc(message)}</p>
    <a class="btn-primary" href="/">Back to search</a>
  </div>
</main>"""
    return page("Not found — FoodSearch", body)


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

MIME_OVERRIDES = {
    ".css": "text/css; charset=utf-8",
    ".webp": "image/webp",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".json": "application/json; charset=utf-8",
}


class FoodSearchHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "FoodSearch/1.0"

    def do_GET(self):
        self._route(head=False)

    def do_HEAD(self):
        self._route(head=True)

    def _route(self, head: bool) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        path = urllib.parse.unquote(parsed.path)
        params = {key: values[-1] for key, values in urllib.parse.parse_qs(parsed.query).items()}

        try:
            if path == "/":
                now = datetime.now(TZ)
                self._send(HTTPStatus.OK, render_index(params, now), "text/html; charset=utf-8",
                           cache="no-store", head=head)
            elif path == "/api/search":
                outcome = search_eateries(params)
                payload = json_api_payload(outcome)
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self._send(HTTPStatus.OK, body, "application/json; charset=utf-8",
                           cache="no-store", head=head)
            elif path == "/api/meta":
                payload = {
                    "city": CITY,
                    "timezone": "Asia/Singapore",
                    "now": datetime.now(TZ).isoformat(),
                    "categories": CATEGORIES,
                    "regions": REGIONS,
                    "popular": POPULAR_SEARCHES,
                    "total": len(EATERIES),
                    "default_center": DEFAULT_CENTER,
                    "note": NOTE,
                }
                self._send(HTTPStatus.OK, json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                           "application/json; charset=utf-8", cache="no-store", head=head)
            elif path == "/health":
                self._send(HTTPStatus.OK, b'{"ok":true}', "application/json; charset=utf-8",
                           cache="no-store", head=head)
            elif path.startswith("/api/eateries/"):
                eatery_id = path[len("/api/eateries/"):].strip("/")
                payload = json_eatery_payload(eatery_id) if re.fullmatch(r"[a-z0-9-]+", eatery_id) else None
                if payload is None:
                    self._send(HTTPStatus.NOT_FOUND,
                               json.dumps({"error": "not_found", "id": eatery_id}).encode("utf-8"),
                               "application/json; charset=utf-8", cache="no-store", head=head)
                else:
                    self._send(HTTPStatus.OK, json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                               "application/json; charset=utf-8", head=head)
            elif path.startswith("/eatery/"):
                eatery_id = path[len("/eatery/"):].strip("/")
                body = render_detail(eatery_id, datetime.now(TZ)) if re.fullmatch(r"[a-z0-9-]+", eatery_id) else None
                if body is None:
                    self._send(HTTPStatus.NOT_FOUND, render_404(), "text/html; charset=utf-8",
                               cache="no-store", head=head)
                else:
                    self._send(HTTPStatus.OK, body, "text/html; charset=utf-8", head=head)
            elif path.startswith("/static/"):
                self._serve_static(path, head=head)
            elif path == "/favicon.ico":
                self._send(HTTPStatus.NO_CONTENT, b"", "image/x-icon", cache="public, max-age=86400", head=head)
            else:
                self._send(HTTPStatus.NOT_FOUND, render_404(), "text/html; charset=utf-8",
                           cache="no-store", head=head)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _serve_static(self, path: str, head: bool = False) -> None:
        relative = path[len("/static/"):]
        target = os.path.normpath(os.path.join(str(STATIC_DIR), relative))
        static_root = str(STATIC_DIR) + os.sep
        if not target.startswith(static_root) or not os.path.isfile(target):
            self._send(HTTPStatus.NOT_FOUND, b"Not found", "text/plain; charset=utf-8", head=head)
            return
        ext = os.path.splitext(target)[1].lower()
        ctype = MIME_OVERRIDES.get(ext) or mimetypes.guess_type(target)[0] or "application/octet-stream"
        cache = "public, max-age=604800" if path.startswith("/static/photos/") else "public, max-age=3600"
        try:
            with open(target, "rb") as fh:
                data = fh.read()
        except OSError:
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, b"Read error", "text/plain; charset=utf-8", head=head)
            return
        self._send(HTTPStatus.OK, data, ctype, cache=cache, head=head)

    def _send(self, status: int, body: bytes, content_type: str, cache: str = "", head: bool = False) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if cache:
            self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
            "base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
        )
        self.end_headers()
        if not head:
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s  %s\n" % (self.log_date_time_string(), fmt % args))


def json_eatery_payload(eatery_id: str) -> dict | None:
    """One listing with its full weekly hours, reviews and photos."""
    eatery = BY_ID.get(eatery_id)
    if not eatery:
        return None
    now = datetime.now(TZ)
    item = public_eatery(eatery, now)
    item["hours_week"] = week_hours(eatery, now)
    item["review_summary"] = {
        "count": item["review_count"],
        "average": item["rating"],
        "shown": len(item["reviews"]),
    }
    return item


def distance_reference(outcome: dict) -> dict | None:
    """Where the reported distances are measured from, if anywhere."""
    if outcome["sort"] != "distance":
        return None
    if outcome["origin"]:
        return {"lat": outcome["origin"][0], "lng": outcome["origin"][1], "source": "browser"}
    return {
        "lat": DEFAULT_CENTER["lat"],
        "lng": DEFAULT_CENTER["lng"],
        "source": "city_centre",
        "label": DEFAULT_CENTER.get("label", ""),
    }


def json_api_payload(outcome: dict) -> dict:
    now = outcome["now"]
    origin = outcome["origin"]
    return {
        "meta": {
            "query": outcome["query"],
            "category": outcome["category"],
            "region": outcome["region"],
            "sort": outcome["sort"],
            "open_only": outcome["open_only"],
            "relaxed": outcome["relaxed"],
            "count": outcome["count"],
            "total": len(EATERIES),
            "now": now.isoformat(),
            "timezone": "Asia/Singapore",
            "origin": {"lat": origin[0], "lng": origin[1]} if origin else None,
            "distance_reference": distance_reference(outcome),
            "city": CITY,
            "note": NOTE,
        },
        "results": outcome["results"],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="FoodSearch — nearby food in Singapore")
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "127.0.0.1"),
        help="bind address (defaults to $HOST, else 127.0.0.1; use 0.0.0.0 in a container)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8000")),
        help="port to listen on (defaults to $PORT, else 8000)",
    )
    parser.add_argument("--open", action="store_true", help="open the app in your browser")
    parser.add_argument(
        "--single-port",
        action="store_true",
        help="fail instead of stepping to the next free port (the platform probes one port)",
    )
    args = parser.parse_args(argv)

    if not EATERIES:
        print(f"error: no eateries found in {DATA_FILE}", file=sys.stderr)
        return 1

    httpd = None
    port = args.port
    candidates = range(args.port, args.port + 1) if args.single_port else range(args.port, args.port + 10)
    for candidate in candidates:
        try:
            httpd = ThreadingHTTPServer((args.host, candidate), FoodSearchHandler)
            port = candidate
            break
        except OSError:
            continue
    if httpd is None:
        print(f"error: could not bind {args.host}:{args.port}", file=sys.stderr)
        return 1

    display_host = "localhost" if args.host in ("127.0.0.1", "0.0.0.0") else args.host
    url = f"http://{display_host}:{port}/"
    print(f"FoodSearch running at {url}")
    print(f"  {len(EATERIES)} eateries · {len(CATEGORIES)} categories · press Ctrl+C to stop")
    if args.open:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())