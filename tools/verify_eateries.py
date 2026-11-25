#!/usr/bin/env python3
"""Remove listings that are closed, demolished, or were never verifiable.

Context: an earlier expansion generated venues from memory. Some were real but
have since closed (JCube, Liang Court, Turf City); many others were invented to
fill out regions. Shipping invented restaurants with fabricated addresses and
reviews is worse than having a smaller dataset, so they are removed here.

Every listing that survives is either (a) in the original curated dataset or
(b) a Singapore landmark whose existence is well established (hawker centres,
market food centres). Confirm operating status before treating any as live.

    python3 tools/verify_eateries.py            # audit, change nothing
    python3 tools/verify_eateries.py --apply    # remove offenders
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "backend", "data", "eateries.json")

# Verified closed or demolished (Wikipedia, checked 2026-11-25).
CLOSED = {
    "jcube-jurong-food-court":
        "JCube closed 6 Aug 2023; demolished for the J'Den redevelopment.",
    "tampopo-ramen-liang-court":
        "Liang Court closed 1 Apr 2020; demolished for CanningHill Piers.",
    "grandstand-turf-city":
        "Turf City tenants vacated by end-2024 for redevelopment.",
}

# Venues generated from memory that could not be confirmed as real businesses.
UNVERIFIED = {
    "marsiling-cafe-lunch": "Invented name; no such cafe established.",
    "khatib-plaza-cafe": "Invented name.",
    "admiralty-coffee-shop": "Invented name.",
    "woodlands-kopitiam-street": "Invented name.",
    "kovan-coffee-shop": "Invented name.",
    "hougang-green-kopitiam": "Invented name.",
    "little-india-kopitiam": "Invented name.",
    "tanjong-pagar-cafe": "Invented name.",
    "orchard-lunch-cafe": "Invented name.",
    "clarke-quay-cafe": "Invented name.",
    "raffles-place-cafe": "Invented name.",
    "sims-avenue-cafe": "Invented name.",
    "serangoon-garden-cafe": "Invented name.",
    "pioneer-mall-cafe": "Invented name.",
    "eastpoint-seafood": "Invented restaurant.",
    "sengkang-square-food-hall": "Invented venue.",
    "sengkang-compassvale-food-court": "Invented venue.",
    "khatib-bongsu-cafe": "Invented venue.",
    "yishun-park-nasi-lemak": "Invented stall.",
    "admiralty-place-food-court": "Invented venue.",
    "joo-chiat-59-market": "Invented venue.",
    "siglap-upper-east-coast-food-centre": "Invented venue.",
    "upper-changi-kopitiam": "Invented venue.",
    "jurong-east-hong-kong-cafe": "Invented restaurant.",
    "korean-bibimbap-somerset": "Invented restaurant.",
    "gyoza-ya-bugis": "Invented restaurant.",
    "udon-ya-takashimaya": "Invented restaurant.",
    "naan-curry-hougang": "Invented restaurant.",
    "biryani-pot-tampines": "Invented restaurant.",
    "komala-vilas-jurong": "Invented branch; no such outlet established.",
    "muthu-woodlands": "Invented branch; no such outlet established.",
    "korean-bbq-tanjong-pagar": "Invented outlet; attributed to an existing chain.",
}


def main():
    with open(DATA, encoding="utf-8") as fh:
        data = json.load(fh)

    before = len(data["eateries"])
    offenders = {**CLOSED, **UNVERIFIED}
    present = {e["id"] for e in data["eateries"]}

    print(f"{before} listings; {len(set(offenders) & present)} to remove")
    for eid in sorted(set(offenders) & present):
        kind = "CLOSED" if eid in CLOSED else "UNVERIFIED"
        print(f"  {kind:10} {eid:38} {offenders[eid]}")

    if "--apply" not in sys.argv:
        print("\n(dry run — pass --apply to remove)")
        return 0

    data["eateries"] = [e for e in data["eateries"] if e["id"] not in offenders]
    with open(DATA, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)

    counts = {}
    for e in data["eateries"]:
        counts[e["region"]] = counts.get(e["region"], 0) + 1
    print(f"\nremoved {before - len(data['eateries'])}; {len(data['eateries'])} remain")
    print("regions:", {k: counts[k] for k in sorted(counts)})
    return 0


if __name__ == "__main__":
    sys.exit(main())