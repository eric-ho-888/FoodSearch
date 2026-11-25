#!/usr/bin/env python3
"""Populate .cache/commons/<slug>.json with candidate photos from Commons search.

tools/fetch_photos.py resolves one Wikipedia article per dish, which yields a
single image. Scaling to hundreds of listings needs many distinct images per
dish, so this queries the Commons file search instead and stores the same
entry shape repick_photos.py already reads.

Usage:
    python3 tools/fetch_commons_candidates.py            # every slug used by data
    python3 tools/fetch_commons_candidates.py --min 30   # ensure at least N each
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "backend", "data", "eateries.json")
CACHE = os.path.join(ROOT, ".cache", "commons")
API = "https://commons.wikimedia.org/w/api.php"
UA = "FoodSearchDemo/1.0 (local demo app)"

# Query -> Commons search terms. The slug is what photo_queries in the dataset
# refer to; the terms are what we actually search for.
SEARCH_TERMS = {
    "bak-chor-mee": "bak chor mee",
    "bak-kut-teh": "bak kut teh",
    "black-pepper-crab": "black pepper crab",
    "brunch-cafe-food": "brunch cafe food",
    "char-kway-teow": "char kway teow",
    "cheese-platter": "cheese platter",
    "chicken-satay": "chicken satay",
    "chilli-crab-singapore": "chilli crab",
    "croissant": "croissant bakery",
    "dim-sum": "dim sum",
    "fish-head-curry": "fish head curry",
    "french-pasta": "pasta dish restaurant",
    "hainanese-chicken-rice": "hainanese chicken rice",
    "korean-barbecue": "korean barbecue",
    "korean-fried-chicken": "korean fried chicken",
    "laksa": "laksa",
    "mango-sago": "mango sago dessert",
    "mee-rebus": "mee rebus",
    "murtabak": "murtabak",
    "nasi-lemak": "nasi lemak",
    "nasi-padang": "nasi padang",
    "pancakes-breakfast": "pancakes breakfast",
    "ramen-bowl": "ramen bowl",
    "roti-prata": "roti prata",
    "sandwich-cafe": "sandwich cafe",
    "satay": "satay",
    "sundubu-jjigae": "sundubu jjigae",
    "sushi-platter": "sushi platter",
    "thosai": "thosai dosa",
    "tonkotsu-ramen": "tonkotsu ramen",
    "unagi-don": "unagi don",
    # Added with the coffee-shop and restaurant expansion.
    "bak-chor-mee-dry": "mee pok noodles",
    "banana-leaf-rice": "banana leaf rice",
    "biryani": "biryani",
    "burger": "burger",
    "chicken-curry": "chicken curry",
    "coffee-shop": "kopitiam coffee shop singapore",
    "dessert": "asian dessert",
    "duck-rice": "roast duck rice",
    "economy-rice": "economy rice mixed rice",
    "fish-soup": "fish soup noodles",
    "hokkien-mee": "hokkien mee",
    "kaya-toast": "kaya toast",
    "mee-goreng": "mee goreng",
    "mee-siam": "mee siam",
    "popiah": "popiah",
    "prawn-noodles": "prawn noodles",
    "roast-meat": "roast meat char siew",
    "steamboat": "steamboat hotpot",
    "teh-tarik": "teh tarik",
    "wanton-mee": "wanton mee",
    "western-food": "western food steak",
    "pizza": "pizza",
    "salad-bowl": "salad bowl",
    "tandoori": "tandoori chicken",
    "naan": "naan bread",
    "sashimi": "sashimi",
    "gyoza": "gyoza",
    "bbq-seafood": "grilled seafood",
    "otah": "otak otak",
    "carrot-cake": "carrot cake fried",
    "porridge": "congee porridge",
    "claypot-rice": "claypot rice",
    "cai-fan": "cai fan",
    "ice-cream": "ice cream dessert",
    "cake-slice": "cake slice cafe",
    "curry-puff": "curry puff",
    "roti-canai": "roti canai",
    "beef-noodles": "beef noodle soup",
    "dumplings": "dumplings",
    "rice-bowl": "rice bowl dish",
    "noodles": "noodle soup asian",
    "coffee-latte": "latte coffee cup",
    "soft-drink": "soft drink glass",
    "seafood-pasta": "seafood pasta",
}


def get(url, timeout=30, attempts=6):
    delay = 2.0
    last = None
    for _ in range(attempts):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as exc:  # rate limits are the usual culprit
            last = exc
            time.sleep(delay)
            delay = min(delay * 1.8, 45)
    raise last


def api(params):
    params = dict(params, format="json")
    return json.loads(get(API + "?" + urllib.parse.urlencode(params)).decode("utf-8"))


def search(term, limit=60):
    """Commons file search, returning repick-compatible candidate entries."""
    try:
        payload = api({
            "action": "query",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {term}",
            "gsrnamespace": "6",
            "gsrlimit": str(limit),
            "prop": "imageinfo",
            "iiprop": "url|size|extmetadata",
            "iiurlwidth": "800",
        })
    except Exception as exc:
        print(f"  !! {term}: {exc}", file=sys.stderr)
        return []

    out = []
    for page in (payload.get("query", {}).get("pages") or {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        thumb = info.get("thumburl")
        if not thumb or not (info.get("width") or 0) >= 800:
            continue
        meta = info.get("extmetadata", {})

        def clean(key):
            raw = (meta.get(key) or {}).get("value", "") or ""
            return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", raw)).strip()

        out.append({
            "title": page.get("title", ""),
            "thumb": thumb,
            "descurl": info.get("descriptionurl", ""),
            "width": info.get("width"),
            "artist": clean("Artist") or "Unknown",
            "license": clean("LicenseShortName") or "See Commons page",
            "license_url": clean("LicenseUrl"),
        })
    return out


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def main():
    minimum = 30
    if "--min" in sys.argv:
        minimum = int(sys.argv[sys.argv.index("--min") + 1])

    with open(DATA, encoding="utf-8") as fh:
        eateries = json.load(fh)["eateries"]
    needed = {slug(q) for e in eateries for q in e.get("photo_queries", [])}
    needed |= set(SEARCH_TERMS)

    os.makedirs(CACHE, exist_ok=True)
    for key in sorted(needed):
        path = os.path.join(CACHE, key + ".json")
        existing = []
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                existing = json.load(fh)
        if len(existing) >= minimum:
            print(f"skip  {key} ({len(existing)})")
            continue
        term = SEARCH_TERMS.get(key, key.replace("-", " "))
        found = search(term)
        known = {e["title"] for e in existing}
        merged = existing + [f for f in found if f["title"] not in known]
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(merged, fh, indent=1)
        print(f"  ok  {key}: {len(existing)} -> {len(merged)}  ({term})")
        time.sleep(0.4)
    return 0


if __name__ == "__main__":
    sys.exit(main())