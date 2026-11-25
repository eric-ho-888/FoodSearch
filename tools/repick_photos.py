#!/usr/bin/env python3
"""Re-pick each eatery's two photos so no image is reused across listings.

Reads the Commons search results cached by tools/fetch_photos.py
(.cache/commons/<slug>.json), assigns two distinct files per eatery, downloads
any that aren't on disk yet, and rewrites static/photos/manifest.json.

Usage:
    python3 tools/repick_photos.py --verify    # report reuse, change nothing
    python3 tools/repick_photos.py             # assign + download what's missing
"""

import hashlib
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "backend", "data", "eateries.json")
PHOTOS = os.path.join(ROOT, "backend", "static", "photos")
MANIFEST = os.path.join(PHOTOS, "manifest.json")
CACHE = os.path.join(ROOT, ".cache", "commons")
UA = "FoodSearchDemo/1.0 (local demo app; contact: none)"


# Filenames that suggest packaging, menus or diagrams rather than a plated dish.
OFF_TOPIC = re.compile(
    r"\b(logo|menu|packet|package|packs?|stacked|wrapped|bundle|brand|poster|sign|"
    r"diagram|map|chart|box|carton|tin|can|factory|warehouse|"
    r"stall|seller|vendor|cook|chef|kitchen|bridge|church|building|interior|"
    r"aceh|thai|vietnam|hawaii|tokyo|macau|japan|korea|indonesia|india|"
    r"2019|2020|2021|2022)\b",
    re.IGNORECASE,
)
# A plated dish usually reads better than a bare ingredient or a shopfront.
ON_TOPIC_BONUS = re.compile(
    r"\b(dish|bowl|plate|plated|served|serving|platter|meal|soup|noodles?|rice|"
    r"curry|roast|grilled|fried|satay|dessert|coffee)\b",
    re.IGNORECASE,
)
# Formats that are likely transparency/illustration rather than a photo.
BAD_FORMAT = re.compile(r"\.(png|svg|gif|tif|tiff)$", re.IGNORECASE)


def _words(text):
    return set(re.findall(r"[a-z]+", text.lower()))


def pick_best(options, eatery):
    """Choose the most edible-looking photo, keeping the eatery's own dish names in mind."""
    dish_words = set()
    for value in list(eatery.get("specialties", [])) + list(eatery.get("photo_queries", [])):
        dish_words |= _words(value)

    def score(entry):
        title = entry.get("title", "")
        name = title[5:] if title.startswith("File:") else title
        title_words = _words(name)
        value = 0.0
        value += 3.0 * len(title_words & dish_words)
        if ON_TOPIC_BONUS.search(name):
            value += 1.5
        if OFF_TOPIC.search(name):
            value -= 6
        if BAD_FORMAT.search(name):
            value -= 4
        value += min(int(entry.get("width") or 0), 3000) / 6000  # prefer a reasonable-size original
        return value

    ranked = sorted(options, key=score, reverse=True)
    return ranked[0] if ranked else None


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.md5(fh.read()).hexdigest()


MAX_EDGE = 560          # longest side, plenty for a card or a detail tile
WEBP_QUALITY = 68       # ~28 KB per photo, so 240 photos stay under the cap


def _to_webp(blob, path):
    """Convert downloaded bytes to a small WebP. Falls back to the original JPEG
    when Pillow is unavailable, so the pipeline still works without it."""
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        with open(path, "wb") as fh:
            fh.write(blob)
        return False
    import io
    try:
        with Image.open(io.BytesIO(blob)) as im:
            im = im.convert("RGB")
            w, h = im.size
            scale = MAX_EDGE / max(w, h)
            if scale < 1:
                im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))),
                               Image.LANCZOS)
            im.save(path, "WEBP", quality=WEBP_QUALITY, method=6)
        return True
    except Exception:
        with open(path, "wb") as fh:
            fh.write(blob)
        return False


def download(url, path, attempts=8):
    delay = 3.0
    for attempt in range(attempts):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                blob = response.read()
        except Exception as exc:  # rate limits are the usual culprit
            if attempt == attempts - 1:
                print(f"  !! {os.path.basename(path)}: {exc}", file=sys.stderr)
                return False
            retry_after = getattr(exc, "headers", None)
            wait = delay
            if retry_after is not None:
                value = retry_after.get("Retry-After")
                if value and value.isdigit():
                    wait = max(float(value), delay)
            time.sleep(wait)
            delay = min(delay * 1.8, 45)
            continue
        if len(blob) < 4000 or blob[:3] not in (b"\xff\xd8\xff", b"\x89PN"):
            print(f"  ?? {os.path.basename(path)}: not a usable image "
                  f"({len(blob)} bytes)", file=sys.stderr)
            return False
        return _to_webp(blob, path) or os.path.exists(path)
    return False


def main():
    verify_only = "--verify" in sys.argv
    with open(DATA, encoding="utf-8") as fh:
        eateries = json.load(fh)["eateries"]
    with open(MANIFEST, encoding="utf-8") as fh:
        manifest = json.load(fh)

    candidates = {}
    for eatery in eateries:
        pool = []
        for query in eatery.get("photo_queries", []):
            path = os.path.join(CACHE, slug(query) + ".json")
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as fh:
                for entry in json.load(fh):
                    entry = dict(entry, query=query)
                    if entry.get("title") not in {p.get("title") for p in pool}:
                        pool.append(entry)
        candidates[eatery["id"]] = pool

    # First pass: give every eatery its existing files, so downloads are minimal.
    assigned = {}
    used_titles = set()
    for eatery in eateries:
        eid = eatery["id"]
        entries = manifest.get(eid, [])
        assigned[eid] = []
        for entry in entries[:2]:
            title = entry.get("title")
            path = os.path.join(PHOTOS, entry.get("file", ""))
            if title and title in used_titles or not os.path.exists(path):
                continue
            used_titles.add(title)
            assigned[eid].append(entry)

    changes = []
    for eatery in eateries:
        eid = eatery["id"]
        picks = assigned[eid]
        while len(picks) < 2:
            options = [
                c for c in candidates[eid]
                if c["title"] not in used_titles
                and not any(p.get("title") == c["title"] for p in picks)
            ]
            choice = pick_best(options, eatery)
            if choice is None:
                print(f"  ?? {eid}: no unused cached photo left", file=sys.stderr)
                break
            filename = f"{eid}-{len(picks) + 1}.webp"
            used_titles.add(choice["title"])
            picks.append({
                "file": filename,
                "article": choice["query"],
                "title": choice["title"],
                "source": choice.get("descurl", ""),
                "artist": choice.get("artist", "Unknown"),
                "license": choice.get("license", "See Commons page"),
                "license_url": choice.get("license_url", ""),
                "_thumb": choice.get("thumb"),
            })
            changes.append((eid, filename, choice["title"]))

    if verify_only:
        problems = []
        for eatery in eateries:
            eid = eatery["id"]
            files = [p["file"] for p in manifest.get(eid, [])]
            if len(files) < 2:
                problems.append(f"{eid}: {len(files)} photo(s)")
        print(f"{len(eateries)} eateries · {len(changes)} reassignment(s) needed")
        for problem in problems:
            print("  -", problem)
        for eid, filename, title in changes:
            print(f"  would add {filename}  <- {title}")
        return 0

    for eid, filename, title in changes:
        entry = next(p for p in assigned[eid] if p["file"] == filename)
        thumb = entry.pop("_thumb", None)
        if thumb and not download(thumb, os.path.join(PHOTOS, filename)):
            print(f"  fail {filename} <- {title}", file=sys.stderr)

    # Different Commons titles can hold identical bytes; swap out any repeats.
    seen = {}
    for eatery in eateries:
        eid = eatery["id"]
        picks = assigned[eid]
        for entry in picks:
            entry.pop("_thumb", None)
        for index, entry in enumerate(list(picks)):
            path = os.path.join(PHOTOS, entry["file"])
            if not os.path.exists(path):
                picks.remove(entry)
                continue
            key = digest(path)
            if key not in seen:
                seen[key] = (eid, entry["file"])
                continue
            options = [
                c for c in candidates[eid]
                if c["title"] not in used_titles
                and c["title"] != entry.get("title")
            ]
            choice = pick_best(options, eatery)
            if not choice or not choice.get("thumb"):
                print(f"  ?? {eid}: cannot replace duplicate {entry['file']}", file=sys.stderr)
                continue
            replacement = {
                "file": entry["file"],
                "article": choice["query"],
                "title": choice["title"],
                "source": choice.get("descurl", ""),
                "artist": choice.get("artist", "Unknown"),
                "license": choice.get("license", "See Commons page"),
                "license_url": choice.get("license_url", ""),
            }
            if not download(choice["thumb"], path):
                print(f"  fail replacing {entry['file']}", file=sys.stderr)
                continue
            new_key = digest(path)
            if new_key in seen:
                print(f"  ?? {eid}: replacement for {entry['file']} is also a duplicate",
                      file=sys.stderr)
                continue
            used_titles.discard(entry.get("title"))
            used_titles.add(choice["title"])
            seen[new_key] = (eid, entry["file"])
            picks[index] = replacement
            print(f"  ok  {entry['file']} <- {choice['title']}")

        manifest[eid] = picks

    # Drop files that no longer belong to any listing.
    keep = {p["file"] for picks in assigned.values() for p in picks}
    for name in os.listdir(PHOTOS):
        if name.endswith((".jpg", ".webp")) and name not in keep:
            os.remove(os.path.join(PHOTOS, name))

    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"wrote {MANIFEST} · {len(keep)} photos")
    return 0



if __name__ == "__main__":
    sys.exit(main())