#!/usr/bin/env python3
"""Bundle dish photos for FoodSearch from Wikimedia Commons (stdlib only).

For every eatery, tools/photo_sources.json names two Wikipedia dish articles.
This script resolves each article's lead image, downloads a 900px rendition into
static/photos/, and writes static/photos/manifest.json with attribution data
(artist, licence, Commons page) that the app displays under each photo.

No Google Places / image API is used at runtime — the app serves local files.

Usage:
    python3 tools/fetch_photos.py             # fetch anything missing
    python3 tools/fetch_photos.py --refresh    # re-download everything
    python3 tools/fetch_photos.py --verify     # report coverage only
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "backend", "data", "eateries.json")
SOURCES = os.path.join(ROOT, "tools", "photo_sources.json")
PHOTOS = os.path.join(ROOT, "backend", "static", "photos")
MANIFEST = os.path.join(PHOTOS, "manifest.json")

WP_API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
UA = "FoodSearchDemo/1.0 (local demo app)"


def get(url, timeout=30, attempts=6):
    """GET with exponential backoff — Wikimedia throttles bursty clients (HTTP 429)."""
    delay = 2.0
    last = None
    for _ in range(attempts):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code not in (429, 500, 502, 503, 504):
                raise
            retry = exc.headers.get("Retry-After") if exc.headers else None
            wait = float(retry) if retry and retry.isdigit() else delay
        except (urllib.error.URLError, TimeoutError) as exc:
            last = exc
            wait = delay
        time.sleep(wait)
        delay = min(delay * 2, 60)
    raise last


def api(base, params):
    params = dict(params, format="json")
    return json.loads(get(base + "?" + urllib.parse.urlencode(params)).decode("utf-8"))


def lead_image(article):
    """Return (commons_file_title, thumb_url, description_url) for an article's lead image."""
    page = api(WP_API, {
        "action": "query",
        "titles": article,
        "prop": "pageimages",
        "piprop": "thumbnail|name",
        "pithumbsize": "900",
        "redirects": "1",
    })
    pages = page.get("query", {}).get("pages", {})
    if not pages:
        return None
    info = next(iter(pages.values()))
    thumb = (info.get("thumbnail") or {}).get("source")
    name = info.get("pageimage")
    if not thumb or not name:
        return None
    return name, thumb.split("?")[0], "https://commons.wikimedia.org/wiki/File:" + urllib.parse.quote(name.replace(" ", "_"))


def attribution(name):
    """Look up artist and licence for a Commons file title."""
    try:
        res = api(COMMONS_API, {
            "action": "query",
            "titles": "File:" + name,
            "prop": "imageinfo",
            "iiprop": "extmetadata",
        })
    except Exception:
        return {"artist": "Unknown", "license": "See Commons page", "license_url": ""}
    import re
    pages = res.get("query", {}).get("pages", {})
    info = (next(iter(pages.values()), {}).get("imageinfo") or [{}])[0]
    meta = info.get("extmetadata", {})

    def clean(key):
        raw = (meta.get(key) or {}).get("value", "") or ""
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", raw)).strip()

    return {
        "artist": clean("Artist") or "Unknown",
        "license": clean("LicenseShortName") or "See Commons page",
        "license_url": clean("LicenseUrl"),
    }


def sniff_ext(blob):
    if blob[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if blob[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        return ".webp"
    return ".jpg"


def main():
    refresh = "--refresh" in sys.argv
    verify_only = "--verify" in sys.argv
    os.makedirs(PHOTOS, exist_ok=True)

    with open(DATA, encoding="utf-8") as fh:
        eateries = json.load(fh)["eateries"]
    with open(SOURCES, encoding="utf-8") as fh:
        sources = json.load(fh)["photos"]

    manifest = {}
    if os.path.exists(MANIFEST) and not refresh:
        with open(MANIFEST, encoding="utf-8") as fh:
            manifest = json.load(fh)

    problems = []
    for eatery in eateries:
        eid = eatery["id"]
        articles = sources.get(eid, [])
        if len(articles) < 2:
            problems.append(f"{eid}: needs 2 article names in photo_sources.json")
            continue

        have = [p for p in manifest.get(eid, []) if os.path.exists(os.path.join(PHOTOS, p["file"]))]
        if len(have) >= 2 and not refresh:
            print(f"skip  {eid}")
            continue
        if verify_only:
            problems.append(f"{eid}: only {len(have)} photo(s) on disk")
            continue

        # Remove stale files for this eatery before rewriting.
        for stale in manifest.get(eid, []):
            path = os.path.join(PHOTOS, stale.get("file", ""))
            if os.path.exists(path):
                os.remove(path)

        picks = []
        for idx, article in enumerate(articles[:2], start=1):
            try:
                resolved = lead_image(article)
            except Exception as exc:
                problems.append(f"{eid}/{article}: lookup failed ({exc})")
                continue
            if not resolved:
                problems.append(f"{eid}/{article}: no lead image")
                continue
            name, thumb_url, desc_url = resolved
            try:
                blob = get(thumb_url)
            except Exception as exc:
                problems.append(f"{eid}/{article}: download failed ({exc})")
                continue
            if len(blob) < 4000:
                problems.append(f"{eid}/{article}: tiny file ({len(blob)} bytes)")
                continue
            filename = f"{eid}-{idx}{sniff_ext(blob)}"
            with open(os.path.join(PHOTOS, filename), "wb") as fh:
                fh.write(blob)
            att = attribution(name)
            picks.append({
                "file": filename,
                "article": article,
                "title": name,
                "source": desc_url,
                **att,
            })
            print(f"  ok  {eid}: {filename}  <- {article} ({name})")
            time.sleep(0.8)

        if picks:
            manifest[eid] = picks
        with open(MANIFEST, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)

    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    complete = sum(1 for e in eateries if len(manifest.get(e["id"], [])) >= 2)
    print(f"\n{eateries.__len__()} eateries, {complete} with 2 photos -> {MANIFEST}")
    if problems:
        print("\nProblems:", file=sys.stderr)
        for p in problems:
            print("  -", p, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())