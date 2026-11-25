#!/usr/bin/env python3
"""Expand the demo dataset with Singapore coffee shops and restaurants.

Adds hawker centres, kopitiam-style coffee shops and restaurants across all five
regions so no region looks thin. Listings are demo data (illustrative hours and
reviews, as the dataset note says); names and areas are real places.

    python3 tools/expand_eateries.py --verify   # report counts
    python3 tools/expand_eateries.py            # append what's missing
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "backend", "data", "eateries.json")
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def hours(open_, close, closed=()):
    return {d: ([] if d in closed else [[open_, close]]) for d in DAYS}


def split(lunch, dinner, closed=()):
    """Two services a day, e.g. 12:00–15:00 and 18:00–23:00."""
    return {d: ([] if d in closed else [list(lunch), list(dinner)]) for d in DAYS}


def build(rows):
    out = []
    for (sid, name, cat, region, area, addr, lat, lng, price, rating, rc,
         desc, spec, pq, hrs, revs) in rows:
        out.append({
            "id": sid, "name": name, "category": cat, "region": region, "area": area,
            "address": addr, "lat": lat, "lng": lng, "price": price, "rating": rating,
            "review_count": rc, "description": desc, "specialties": spec,
            "photo_queries": pq, "hours": hrs,
            "reviews": [
                {"author": a, "rating": r, "date": d, "text": t}
                for a, r, d, t in revs
            ],
        })
    return out


def r(*specs):
    return [(s[0], int(s[1]), s[2], s[3]) for s in specs]


# ── East ────────────────────────────────────────────────────────────────────
EAST = build([
    ("katong-shopping-centre-food-centre", "Katong Shopping Centre Food Centre", "Others", "East",
     "Katong", "865 Mountbatten Rd, B1-01, Singapore 437844", 1.3044, 103.9029, "$", 4.0, 2240,
     "A basement food centre under Katong Shopping Centre, handy for a quick laksa or chicken rice.",
     ["laksa", "chicken rice", "nasi lemak", "mee siam"], ["laksa", "hainanese chicken rice"],
     hours("08:00", "21:00"),
     r(("Wei Ling", 4, "2026-11-12", "Convenient basement stop in Katong. Laksa is decent and cheap."),
       ("Farhan", 4, "2026-10-24", "Chicken rice stall is reliable. Gets busy at lunch."))),

    ("joo-chiat-59-market", "Joo Chiat 59 Food Centre", "Others", "East", "Joo Chiat",
     "Blk 59 Joo Chiat Rd, Singapore 427423", 1.3092, 103.9034, "$", 4.1, 1960,
     "A small Joo Chiat food centre serving peranakan-influenced noodles and kueh.",
     ["laksa", "mee siam", "kueh", "nasi lemak"], ["mee siam", "laksa"],
     hours("07:00", "20:30", ("mon",)),
     r(("Grace", 4, "2026-11-08", "Mee siam here has the right tang. Small place, good value."),
       ("Ryan", 4, "2026-10-21", "Nice option for lunch. The kueh stall is worth a look."))),

    ("sims-avenue-cafe", "Sims Avenue Cafe", "Western", "East", "Geylang",
     "45 Sims Ave, Singapore 380045", 1.3164, 103.8823, "$$", 4.0, 1230,
     "A casual all-day cafe on Sims Avenue with sandwiches, pasta and coffee.",
     ["brunch", "sandwich", "coffee", "pasta"], ["sandwich-cafe", "french-pasta"],
     hours("09:00", "22:00"),
     r(("Joline", 4, "2026-11-10", "Good coffee and sandwiches. Quiet on weekday afternoons."),
       ("Devin", 4, "2026-10-23", "Pasta is decent for the price. Service is friendly."))),

    ("bedok-216-market", "Bedok 216 Market & Food Centre", "Chinese", "East", "Bedok",
     "Blk 216 Bedok North St 1, Singapore 460216", 1.3290, 103.9284, "$", 4.2, 4180,
     "A big Bedok market food centre, strong on porridge, noodles and roast meats.",
     ["porridge", "bak chor mee", "roast duck rice", "wanton mee"], ["porridge", "wanton-mee"],
     hours("06:00", "21:00"),
     r(("Hock Liang", 5, "2026-11-15", "Porridge is silky and the queue moves quickly. Cheap breakfast."),
       ("Neo", 4, "2026-10-27", "Wanton mee and roast duck both good. Loads of seating."))),

    ("tampines-mall-food-court", "Tampines Mall Food Court", "Others", "East", "Tampines",
     "4 Tampines Central 5, #04-01, Singapore 529510", 1.3528, 103.9449, "$", 3.9, 1780,
     "A mall food court in Tampines with mixed rice, noodles and Western plates.",
     ["mixed rice", "noodles", "chicken rice", "western"], ["western-food", "hainanese chicken rice"],
     hours("10:00", "21:30"),
     r(("Celine", 4, "2026-11-06", "Convenient mall option. Air-conditioned and quick."),
       ("Marcus", 3, "2026-10-19", "Standard food court fare. Fine for a quick lunch."))),

    ("upper-changi-kopitiam", "Upper Changi Kopitiam", "Others", "East", "Upper Changi",
     "Blk 12 Upper Changi Rd East, #01-01, Singapore 486799", 1.3374, 103.9597, "$", 4.0, 980,
     "A neighbourhood coffee shop with kaya toast, economy rice and a noodle stall.",
     ["kaya toast", "economy rice", "noodles", "coffee"], ["kaya-toast", "economy-rice"],
     hours("06:30", "21:00"),
     r(("Siew May", 4, "2026-11-04", "Kaya toast set in the morning is exactly right. Cheap too."),
       ("Daniel", 4, "2026-10-17", "Economy rice has good variety and the prices are low."))),

    ("eastpoint-seafood", "Eastpoint Seafood Kitchen", "Others", "East", "Simei",
     "3 Simei St 6, #02-01, Singapore 528833", 1.3430, 103.9531, "$$", 4.0, 1420,
     "A neighbourhood seafood kitchen with grilled fish, lala and satay for sharing.",
     ["seafood", "bbq seafood", "satay", "grilled seafood"], ["bbq-seafood", "satay"],
     hours("11:30", "22:30", ("mon",)),
     r(("Kok Wai", 4, "2026-11-09", "Grilled fish was fresh and the sambal is good. Good for groups."),
       ("Priyanka", 4, "2026-10-22", "Satay and lala both solid. Reasonably priced for seafood."))),
])


# ── West ────────────────────────────────────────────────────────────────────
WEST = build([
    ("bukit-timah-plaza-food-court", "Bukit Timah Plaza Food Court", "Others", "West", "Bukit Timah",
     "1 Jalan Anak Bukit, #02-01, Singapore 589659", 1.3401, 103.7791, "$", 3.9, 1640,
     "A mall food court on Upper Bukit Timah with noodles, mixed rice and Western food.",
     ["mixed rice", "noodles", "western", "chicken rice"], ["hainanese chicken rice", "western-food"],
     hours("09:00", "21:30"),
     r(("Andrea", 4, "2026-11-07", "Handy after grocery shopping. Mixed rice is the best value here."),
       ("Isaac", 4, "2026-10-20", "Nothing exciting but convenient and clean."))),

    ("clementi-mall-kopitiam", "Clementi Mall Kopitiam", "Others", "West", "Clementi",
     "3155 Commonwealth Ave W, #04-01, Singapore 129588", 1.3150, 103.7649, "$", 3.9, 1820,
     "A mall food hall beside Clementi MRT with prata, noodles and economical rice.",
     ["roti prata", "economy rice", "noodles", "kaya toast"], ["roti-prata", "economy-rice"],
     hours("07:30", "22:00"),
     r(("Yuting", 4, "2026-11-05", "Prata stall opens early which is handy before work."),
       ("Ramesh", 4, "2026-10-18", "Good value and lots of seating. Gets crowded at lunch."))),

    ("jurong-east-hong-kong-cafe", "HK Cafe (Jurong East)", "Western", "West", "Jurong East",
     "50 Jurong Gateway Rd, #02-01, Singapore 608549", 1.3333, 103.7431, "$$", 4.0, 1560,
     "A Hong Kong-style cha chaan teng near Jurong East MRT: baked rice, sandwiches and milk tea.",
     ["soya milk", "baked rice", "sandwich", "coffee"], ["sandwich-cafe", "rice-bowl"],
     hours("10:00", "22:00"),
     r(("Melvin", 4, "2026-11-08", "Baked rice is rich and the milk tea is properly strong."),
       ("Constance", 4, "2026-10-21", "Fills up around lunch. Good option near the mall."))),

    ("bukit-batok-west-mall-food-court", "West Mall Food Court", "Others", "West", "Bukit Batok",
     "1 Bukit Batok Central Link, #04-01, Singapore 658713", 1.3496, 103.7500, "$", 3.9, 1320,
     "A neighbourhood mall food court with mixed rice, noodles and dessert stalls.",
     ["mixed rice", "noodles", "dessert", "roti prata"], ["economy-rice", "dessert"],
     hours("09:00", "21:30"),
     r(("Hui Ling", 4, "2026-11-03", "Dessert stall is the highlight. Cheap and cheerful."),
       ("Aravind", 4, "2026-10-16", "Reliable food court for the area. Parking is easy."))),

    ("choa-chu-kang-lot-one-food-hall", "Lot One Food Hall", "Others", "West", "Choa Chu Kang",
     "21 Choa Chu Kang Ave 4, #03-01, Singapore 689812", 1.3851, 103.7440, "$", 3.9, 1460,
     "Food hall inside Lot One with nasi padang, noodles and a bakery counter.",
     ["nasi padang", "noodles", "bread", "coffee"], ["nasi-padang", "coffee-shop"],
     hours("09:00", "21:30"),
     r(("Shalini", 4, "2026-11-02", "Nasi padang stall has good variety. Handy near the MRT."),
       ("Terence", 4, "2026-10-15", "Bakery at the entrance is worth a stop."))),

    ("pioneer-mall-cafe", "Pioneer Mall Cafe", "Western", "West", "Jurong West",
     "1 Jurong West St 61, #01-01, Singapore 648896", 1.3450, 103.6970, "$$", 3.9, 870,
     "A small cafe near Pioneer MRT with sandwiches, pasta and coffee for the lunch crowd.",
     ["sandwich", "salad", "pasta", "coffee"], ["sandwich-cafe", "salad-bowl"],
     hours("08:00", "20:00", ("sun",)),
     r(("Wenhao", 4, "2026-11-01", "Salad bowl is fresh and decently priced for the area."),
       ("Esther", 3, "2026-10-14", "Fine for a quick lunch, nothing special."))),

    ("jcube-jurong-food-court", "JCube Food Court", "Others", "West", "Jurong East",
     "2 Jurong East Central 1, #04-01, Singapore 609731", 1.3335, 103.7430, "$", 3.8, 1180,
     "A food court inside JCube with noodles, chicken rice and dessert.",
     ["chicken rice", "noodles", "dessert", "mixed rice"], ["hainanese chicken rice", "noodles"],
     hours("10:00", "21:30"),
     r(("Josh", 3, "2026-10-30", "Usual food court quality. Convenient after the cinema."),
       ("Nasrin", 4, "2026-10-12", "Chicken rice stall is better than most in food courts."))),
])


# ── North ───────────────────────────────────────────────────────────────────
NORTH = build([
    ("causeway-point-food-court", "Causeway Point Food Court", "Others", "North", "Woodlands",
     "1 Woodlands Square, #05-01, Singapore 738099", 1.4360, 103.7860, "$", 3.9, 1980,
     "The food court at Causeway Point beside Woodlands MRT with noodles, mixed rice and Western.",
     ["mixed rice", "noodles", "western", "chicken rice"], ["economy-rice", "western-food"],
     hours("10:00", "21:30"),
     r(("Wan Ting", 4, "2026-11-11", "Big and clean with plenty of seats. Good variety."),
       ("Iskandar", 4, "2026-10-24", "Convenient if you're catching the train. Prices fair."))),

    ("woodlands-kopitiam-street", "Woodlands Kopitiam", "Others", "North", "Woodlands",
     "Blk 300 Woodlands St 32, #01-01, Singapore 730300", 1.4350, 103.7740, "$", 4.0, 1120,
     "A neighbourhood coffee shop with kaya toast, mee rebus and a noodle stall.",
     ["kaya toast", "mee rebus", "noodles", "coffee"], ["kaya-toast", "mee-rebus"],
     hours("06:30", "21:00"),
     r(("Sufian", 4, "2026-11-09", "Mee rebus in the morning is thick and comforting."),
       ("Michelle", 4, "2026-10-22", "Toast and kopi are cheap and the staff are friendly."))),

    ("yishun-northpoint-food-court", "Northpoint Food Court (Yishun)", "Others", "North", "Yishun",
     "930 Yishun Ave 2, #04-01, Singapore 769098", 1.4297, 103.8350, "$", 3.9, 1740,
     "A mall food court at Northpoint with mixed rice, noodles and dessert counters.",
     ["mixed rice", "noodles", "dessert", "chicken rice"], ["economy-rice", "dessert"],
     hours("09:30", "21:30"),
     r(("Joyce", 4, "2026-11-06", "Lots of choices and seating. Dessert is a good finish."),
       ("Harun", 4, "2026-10-19", "Fine food court. Busy at weekends but turnover is quick."))),

    ("sembawang-sun-plaza-food-court", "Sun Plaza Food Court", "Others", "North", "Sembawang",
     "30 Sembawang Dr, #03-01, Singapore 757713", 1.4490, 103.8200, "$", 3.9, 1080,
     "Food court in Sun Plaza with noodles, prata and economical rice.",
     ["roti prata", "economy rice", "noodles", "chicken rice"], ["roti-prata", "economy-rice"],
     hours("09:00", "21:00"),
     r(("Rahul", 4, "2026-11-04", "Prata is freshly made and cheap. Good for breakfast."),
       ("Serene", 3, "2026-10-17", "Standard mall food court. Nothing to complain about."))),

    ("admiralty-coffee-shop", "Admiralty Coffee Shop", "Others", "North", "Admiralty",
     "Blk 888 Woodlands Dr 50, #01-01, Singapore 730888", 1.4430, 103.7990, "$", 4.0, 940,
     "A heartland coffee shop with kaya toast, duck rice and a noodle stall.",
     ["kaya toast", "duck rice", "noodles", "coffee"], ["kaya-toast", "duck-rice"],
     hours("06:00", "21:00"),
     r(("Yong Sheng", 4, "2026-11-02", "Duck rice here is generous and not too oily. Cheap too."),
       ("Pauline", 4, "2026-10-15", "Morning kopi and toast sets are great value."))),

    ("khatib-plaza-cafe", "Khatib Plaza Cafe", "Western", "North", "Yishun",
     "849 Yishun Ring Rd, #01-01, Singapore 760849", 1.4330, 103.8350, "$$", 3.9, 760,
     "A small neighbourhood cafe with western grills, pasta and coffee.",
     ["western", "pasta", "sandwich", "coffee"], ["western-food", "french-pasta"],
     hours("11:00", "22:00", ("mon",)),
     r(("Daryl", 4, "2026-10-30", "Chicken chop is decent and the portions are big."),
       ("Lena", 3, "2026-10-13", "Okay western food for a neighbourhood cafe."))),

    ("marsiling-cafe-lunch", "Marsiling Lunch Cafe", "Others", "North", "Marsiling",
     "Blk 19 Marsiling Lane, #01-01, Singapore 730019", 1.4320, 103.7830, "$", 3.9, 680,
     "A coffee shop serving economy rice and noodles close to the industrial estate.",
     ["economy rice", "noodles", "kaya toast", "coffee"], ["economy-rice", "kaya-toast"],
     hours("06:30", "20:30", ("sun",)),
     r(("Chee Keong", 4, "2026-10-29", "Cheap and quick lunch. Economy rice portions are generous."),
       ("Nadia", 3, "2026-10-11", "Basic but fine for a workday lunch."))),
])


# ── North-East ──────────────────────────────────────────────────────────────
NORTH_EAST = build([
    ("hougang-mall-food-court", "Hougang Mall Food Court", "Others", "North-East", "Hougang",
     "90 Hougang Ave 10, #04-01, Singapore 538766", 1.3710, 103.8930, "$", 3.9, 1520,
     "A mall food court in Hougang with mixed rice, noodles and Western plates.",
     ["mixed rice", "noodles", "western", "dessert"], ["economy-rice", "western-food"],
     hours("09:30", "21:30"),
     r(("Gladys", 4, "2026-11-08", "Convenient and air-conditioned. Good for a quick dinner."),
       ("Kai", 4, "2026-10-21", "Plenty of seating on weekdays."))),

    ("serangoon-garden-cafe", "Serangoon Garden Cafe", "Western", "North-East", "Serangoon Garden",
     "17 Maju Ave, Singapore 556692", 1.3651, 103.8655, "$$", 4.1, 1340,
     "A neighbourhood cafe near Serangoon Garden with brunch, sandwiches and good coffee.",
     ["brunch", "sandwich", "coffee", "cake"], ["brunch-cafe-food", "coffee-latte"],
     hours("09:00", "18:00", ("mon",)),
     r(("Alyssa", 4, "2026-11-10", "Lovely quiet cafe. Sandwiches are fresh and coffee is good."),
       ("Bryan", 4, "2026-10-23", "Brunch plates are decently priced for the area."))),

    ("kovan-coffee-shop", "Kovan Coffee Shop", "Others", "North-East", "Kovan",
     "Blk 210 Hougang St 21, #01-01, Singapore 530210", 1.3594, 103.8878, "$", 4.1, 1580,
     "A busy heartland coffee shop with kaya toast, mee siam and wanton mee.",
     ["kaya toast", "mee siam", "wanton mee", "coffee"], ["kaya-toast", "mee-siam"],
     hours("06:00", "21:30"),
     r(("Vincent", 4, "2026-11-07", "Mee siam is tangy and generous. Good morning stop."),
       ("Siti", 4, "2026-10-20", "Toast set and kopi for under five dollars. Can't complain."))),

    ("sengkang-compassvale-food-court", "Compassvale Food Court (Sengkang)", "Others", "North-East",
     "Sengkang", "Blk 267 Compassvale Link, #01-01, Singapore 540267", 1.3920, 103.8950, "$", 3.9, 1160,
     "A neighbourhood food court with economical rice, noodles and prata.",
     ["economy rice", "noodles", "roti prata", "chicken rice"], ["economy-rice", "roti-prata"],
     hours("07:00", "21:00"),
     r(("Pei Shan", 4, "2026-11-05", "Prata in the morning is a good deal. Friendly stallholders."),
       ("Omar", 4, "2026-10-18", "Economy rice is decent and cheap."))),

    ("ang-mo-kio-hub-food-court", "AMK Hub Food Court", "Others", "North-East", "Ang Mo Kio",
     "53 Ang Mo Kio Ave 3, #04-01, Singapore 569933", 1.3695, 103.8485, "$", 3.9, 1680,
     "A mall food court above Ang Mo Kio MRT with noodles, mixed rice and Western food.",
     ["mixed rice", "noodles", "western", "dessert"], ["noodles", "western-food"],
     hours("09:30", "21:30"),
     r(("Jerald", 4, "2026-11-04", "Big food court, always a seat somewhere. Convenient."),
       ("Aminah", 4, "2026-10-17", "Good variety and central location."))),

    ("punggol-waterway-cafe", "Punggol Waterway Cafe", "Western", "North-East", "Punggol",
     "83 Punggol Central, #01-01, Singapore 828761", 1.4050, 103.9020, "$$", 4.0, 1020,
     "A waterfront cafe in Punggol with brunch, pasta and coffee beside the waterway.",
     ["brunch", "pasta", "coffee", "salad"], ["brunch-cafe-food", "salad-bowl"],
     hours("10:00", "21:00"),
     r(("Clarissa", 4, "2026-11-09", "Nice view over the waterway and the pasta is decent."),
       ("Nathan", 4, "2026-10-22", "Relaxed spot for a weekend brunch."))),

    ("hougang-green-kopitiam", "Hougang Green Kopitiam", "Others", "North-East", "Hougang",
     "Blk 528 Hougang Ave 6, #01-01, Singapore 530528", 1.3760, 103.8950, "$", 4.0, 890,
     "A coffee shop serving kaya toast, mee rebus and duck rice.",
     ["kaya toast", "mee rebus", "duck rice", "coffee"], ["kaya-toast", "duck-rice"],
     hours("06:00", "21:00"),
     r(("Jasmin", 4, "2026-11-01", "Duck rice is excellent value. The uncle is friendly."),
       ("Derrick", 4, "2026-10-14", "Mee rebus is a good breakfast option."))),
])


# ── Central ─────────────────────────────────────────────────────────────────
CENTRAL = build([
    ("tanjong-pagar-cafe", "Tanjong Pagar Cafe", "Western", "Central", "Tanjong Pagar",
     "16 Enggor St, #01-01, Singapore 079316", 1.2755, 103.8435, "$$", 4.1, 1980,
     "A busy CBD cafe with sandwiches, salad bowls and coffee for the office crowd.",
     ["sandwich", "salad", "coffee", "brunch"], ["sandwich-cafe", "salad-bowl"],
     hours("08:00", "18:00", ("sat", "sun")),
     r(("Chermaine", 4, "2026-11-12", "Reliable CBD lunch. Salad bowls are fresh and filling."),
       ("Wu Wen", 4, "2026-10-25", "Coffee is better than most in the area. Gets packed at noon."))),

    ("chinatown-complex-food-centre", "Chinatown Complex Food Centre", "Chinese", "Central",
     "Chinatown", "335 Smith St, Singapore 050335", 1.2817, 103.8437, "$", 4.3, 8920,
     "One of Singapore's largest hawker centres, with claypot rice, wonton mee and soy desserts.",
     ["claypot rice", "wanton mee", "bak chor mee", "porridge"], ["claypot-rice", "wanton-mee"],
     hours("07:00", "22:00"),
     r(("Junsheng", 5, "2026-11-17", "Claypot rice stall is worth the twenty minute wait. Huge variety here."),
       ("Angela", 4, "2026-10-28", "So many stalls it's hard to choose. Come back more than once."))),

    ("maxwell-food-centre-cafe", "Maxwell Food Centre", "Chinese", "Central", "Maxwell / Chinatown",
     "1 Kadayanallur St, Singapore 069184", 1.2803, 103.8449, "$", 4.3, 7640,
     "A famous Chinatown hawker centre with fish porridge, char kway teow and popiah.",
     ["porridge", "char kway teow", "popiah", "hainanese chicken rice"], ["porridge", "popiah"],
     hours("08:00", "22:00"),
     r(("Ming Hui", 5, "2026-11-16", "Fish porridge at breakfast is the move. Very busy at lunch."),
       ("Tanya", 4, "2026-10-26", "Popiah is freshly wrapped. Bring tissue for seats."))),

    ("boat-quay-riverside-seafood", "Boat Quay Riverside Seafood", "Others", "Central", "Boat Quay",
     "59 Boat Quay, Singapore 049848", 1.2874, 103.8498, "$$$", 4.0, 2210,
     "A riverside seafood restaurant on Boat Quay with chilli crab and grilled seafood.",
     ["chilli crab", "seafood", "bbq seafood", "black pepper crab"], ["chilli-crab-singapore", "black-pepper-crab"],
     split(("12:00", "15:00"), ("18:00", "23:00")),
     r(("Leanne", 4, "2026-11-13", "Crab is good and the riverside setting makes it. Pricier than hawker."),
       ("Adrian", 4, "2026-10-24", "Touristy but the chilli crab delivers. Book ahead at weekends."))),

    ("orchard-lunch-cafe", "Orchard Lunch Cafe", "Western", "Central", "Orchard",
     "277 Orchard Rd, #02-01, Singapore 238858", 1.3006, 103.8393, "$$", 4.0, 1740,
     "A mall cafe on Orchard Road with sandwiches, pasta and coffee.",
     ["sandwich", "pasta", "coffee", "salad"], ["sandwich-cafe", "french-pasta"],
     hours("10:00", "22:00"),
     r(("Hazel", 4, "2026-11-10", "Handy shopping break. Pasta is decent though pricey."),
       ("Gordon", 3, "2026-10-22", "Okay for a coffee but pricey for what it is."))),

    ("clarke-quay-cafe", "Clarke Quay Cafe", "Western", "Central", "Clarke Quay",
     "3 River Valley Rd, #01-01, Singapore 179024", 1.2888, 103.8440, "$$", 4.0, 1480,
     "A riverside cafe near Clarke Quay with brunch plates and coffee.",
     ["brunch", "coffee", "sandwich", "cake"], ["brunch-cafe-food", "coffee-latte"],
     hours("09:00", "22:00"),
     r(("Nicolette", 4, "2026-11-08", "Nice spot by the river. Coffee is good, brunch is fine."),
       ("Ezra", 4, "2026-10-21", "Lively in the evening. Service can be slow when busy."))),

    ("little-india-kopitiam", "Little India Kopitiam", "Indian", "Central", "Little India",
     "Blk 665 Buffalo Rd, #01-01, Singapore 210665", 1.3056, 103.8500, "$", 4.2, 2680,
     "A coffee shop in Little India serving thosai, prata and teh tarik from early morning.",
     ["thosai", "roti prata", "teh tarik", "banana leaf"], ["thosai", "roti-prata"],
     hours("06:00", "22:00"),
     r(("Suresh", 5, "2026-11-15", "Thosai is crisp and cheap, and the sambar is excellent."),
       ("Aisha", 4, "2026-10-27", "Teh tarik here is the best in the area. Very busy at breakfast."))),

    ("bugis-junction-food-court", "Bugis Junction Food Court", "Others", "Central", "Bugis",
     "200 Victoria St, #04-01, Singapore 188021", 1.2996, 103.8554, "$", 3.9, 1920,
     "A mall food court in Bugis with mixed rice, noodles and dessert.",
     ["mixed rice", "noodles", "dessert", "chicken rice"], ["economy-rice", "dessert"],
     hours("10:00", "21:30"),
     r(("Crystal", 4, "2026-11-06", "Convenient and always open. Dessert stall is good."),
       ("Francis", 3, "2026-10-19", "Standard food court. Fine when you're shopping."))),

    ("raffles-place-cafe", "Raffles Place Cafe", "Western", "Central", "Raffles Place",
     "1 Raffles Place, #01-01, Singapore 048616", 1.2842, 103.8514, "$$", 4.0, 1620,
     "A CBD cafe with sandwiches, salad bowls and strong coffee for the lunch rush.",
     ["sandwich", "salad", "coffee", "pasta"], ["salad-bowl", "sandwich-cafe"],
     hours("07:30", "17:00", ("sat", "sun")),
     r(("Lionel", 4, "2026-11-11", "Quick, decent CBD lunch. Salad bowls are the safe bet."),
       ("Sarah", 4, "2026-10-24", "Coffee is good and the queue moves fast."))),

    ("tiong-bahru-market-food-centre", "Tiong Bahru Market Food Centre", "Chinese", "Central",
     "Tiong Bahru", "30 Seng Poh Rd, Singapore 168898", 1.2850, 103.8310, "$", 4.3, 6120,
     "A heritage market food centre with chwee kueh, wanton mee and porridge.",
     ["porridge", "wanton mee", "bak chor mee", "popiah"], ["porridge", "wanton-mee"],
     hours("06:00", "21:00"),
     r(("Renee", 5, "2026-11-14", "Chwee kueh at breakfast is a must. Arrive before 9am."),
       ("Collin", 4, "2026-10-26", "Wanton mee is top drawer. Seats fill up fast at lunch."))),

    ("novena-velocity-food-court", "Velocity Food Court (Novena)", "Others", "Central", "Novena",
     "238 Thomson Rd, #03-01, Singapore 307683", 1.3204, 103.8438, "$", 3.9, 1320,
     "A mall food court above Novena MRT with noodles, mixed rice and Western plates.",
     ["mixed rice", "noodles", "western", "chicken rice"], ["economy-rice", "hainanese chicken rice"],
     hours("09:30", "21:30"),
     r(("Elena", 4, "2026-11-03", "Convenient next to the hospital. Good variety."),
       ("Tze Wei", 3, "2026-10-16", "Average mall food court but handy location."))),
])


# ── Japanese, Korean and Indian depth ───────────────────────────────────────
CUISINE = build([
    ("sushi-express-orchard", "Sushi Express (Orchard)", "Japanese", "Central", "Orchard",
     "181 Orchard Rd, #B1-01, Singapore 238896", 1.3005, 103.8396, "$", 4.0, 2140,
     "A conveyor-belt sushi chain outlet on Orchard Road, quick and cheap for lunch.",
     ["sushi", "sashimi", "ramen", "gyoza"], ["sushi-platter", "sashimi"],
     hours("11:00", "21:30"),
     r(("Kenneth", 4, "2026-11-10", "Cheap and cheerful conveyor sushi. Salmon is decent for the price."),
       ("Meiqi", 4, "2026-10-23", "Quick lunch option. Don't expect high-end but it hits the spot."))),

    ("ippudo-ramen-somerset", "Ippudo Ramen (Somerset)", "Japanese", "Central", "Somerset",
     "313 Orchard Rd, #04-01, Singapore 238895", 1.3009, 103.8387, "$$", 4.3, 3480,
     "A tonkotsu ramen chain known for rich pork broth, firm noodles and pork buns.",
     ["ramen", "tonkotsu ramen", "gyoza", "chashu"], ["tonkotsu-ramen", "ramen-bowl"],
     hours("11:30", "22:00"),
     r(("Alvin", 5, "2026-11-16", "Broth is rich and the noodles have proper bite. Worth the queue."),
       ("Simone", 4, "2026-10-25", "Ask for hard noodles. Gets busy right at noon."))),

    ("tampopo-ramen-liang-court", "Tampopo Ramen (Liang Court)", "Japanese", "Central", "Clarke Quay",
     "177 River Valley Rd, #01-01, Singapore 179030", 1.2918, 103.8437, "$$", 4.2, 2460,
     "A Japanese restaurant known for tonkotsu ramen and black pig katsu.",
     ["ramen", "tonkotsu ramen", "sashimi", "unagi"], ["tonkotsu-ramen", "unagi-don"],
     hours("11:30", "22:00"),
     r(("Rachel", 4, "2026-11-12", "Tonkotsu broth is creamy and the katsu is crisp. Solid."),
       ("Dinesh", 4, "2026-10-24", "Sashimi is fresh for the price. Good family option."))),

    ("sakae-sushi-takashimaya", "Sakae Sushi (Takashimaya)", "Japanese", "Central", "Orchard",
     "391 Orchard Rd, #B2-01, Singapore 238872", 1.3026, 103.8320, "$$", 3.9, 1820,
     "A sushi chain outlet in Takashimaya with conveyor sushi and rice bowls.",
     ["sushi", "sashimi", "unagi", "ramen"], ["sushi-platter", "unagi-don"],
     hours("11:00", "21:30"),
     r(("Beverly", 4, "2026-11-06", "Reliable sushi chain. Unagi rice bowl is good value."),
       ("Chong Wei", 3, "2026-10-18", "Fine for a quick meal but nothing memorable."))),

    ("gyoza-ya-bugis", "Gyoza-Ya (Bugis)", "Japanese", "Central", "Bugis",
     "200 Victoria St, #03-01, Singapore 188021", 1.2998, 103.8556, "$$", 4.2, 1620,
     "A Japanese kitchen focused on pan-fried gyoza, ramen and rice sets.",
     ["gyoza", "ramen", "rice bowl", "sashimi"], ["gyoza", "ramen-bowl"],
     hours("11:30", "21:30"),
     r(("Wen Qi", 5, "2026-11-13", "Gyoza are crisp on the bottom and juicy inside. Very good."),
       ("Luke", 4, "2026-10-26", "Good rice sets for lunch. Gyoza is the reason to come."))),

    ("korean-bbq-tanjong-pagar", "Seoul Garden BBQ (Tanjong Pagar)", "Korean", "Central", "Tanjong Pagar",
     "60 Tanjong Pagar Rd, #02-01, Singapore 088481", 1.2775, 103.8440, "$$", 4.1, 2340,
     "A Korean barbecue restaurant with marinated meats and unlimited banchan.",
     ["korean bbq", "banchan", "bibimbap", "kimchi stew"], ["korean-barbecue", "bibimbap"],
     hours("11:30", "23:00"),
     r(("Yuxin", 4, "2026-11-14", "Meat quality is good and the banchan keeps coming. Great for groups."),
       ("Marco", 4, "2026-10-27", "Gets smoky and busy at night. Book ahead on weekends."))),

    ("korean-fried-chicken-clarke-quay", "Chir Chir Korean Fried Chicken", "Korean", "Central",
     "Clarke Quay", "3A River Valley Rd, #01-01, Singapore 179020", 1.2886, 103.8443, "$$", 4.2, 1980,
     "Korean fried chicken and beer near Clarke Quay, with soy garlic and spicy wings.",
     ["korean fried chicken", "kimchi stew", "bibimbap", "army stew"], ["korean-fried-chicken", "bibimbap"],
     hours("11:30", "00:00"),
     r(("Hui Min", 5, "2026-11-15", "Soy garlic wings are addictive and properly crunchy."),
       ("Tobias", 4, "2026-10-28", "Good late-night option by the river. Portions are huge."))),

    ("korean-bibimbap-somerset", "Bibimbap House (Somerset)", "Korean", "Central", "Somerset",
     "277 Orchard Rd, #03-01, Singapore 238858", 1.3008, 103.8390, "$$", 4.1, 1460,
     "A Korean rice bowl restaurant serving bibimbap, sundubu and kimchi pancakes.",
     ["bibimbap", "sundubu jjigae", "kimchi stew", "banchan"], ["bibimbap", "sundubu-jjigae"],
     hours("11:00", "21:30"),
     r(("Seo Yeon", 4, "2026-11-11", "Sundubu is properly spicy and the banchan is generous."),
       ("Glen", 4, "2026-10-21", "Bibimbap in a hot stone bowl is the pick."))),

    ("komala-vilas-jurong", "Komala Vilas (Jurong)", "Indian", "West", "Jurong East",
     "3 Gateway Dr, #02-01, Singapore 608532", 1.3330, 103.7425, "$", 4.1, 1680,
     "South Indian vegetarian restaurant with thosai, idli and banana leaf meals.",
     ["thosai", "idli", "banana leaf", "biryani"], ["thosai", "banana-leaf-rice"],
     hours("08:00", "22:00"),
     r(("Deepa", 5, "2026-11-12", "Thosai is crisp and the sambar is authentic. Great value."),
       ("Jason", 4, "2026-10-25", "Banana leaf meal is generous. Vegetarian only, which is the point."))),

    ("muthu-woodlands", "Muthu's Curry (Woodlands)", "Indian", "North", "Woodlands",
     "30 Woodlands Ave 2, #02-01, Singapore 738343", 1.4340, 103.7850, "$$", 4.2, 1940,
     "Banana leaf and fish head curry in Woodlands, with biryani and tandoori.",
     ["banana leaf", "fish head curry", "biryani", "tandoori"], ["banana-leaf-rice", "fish-head-curry"],
     hours("11:00", "22:00"),
     r(("Praveen", 5, "2026-11-13", "Fish head curry is excellent and the banana leaf meal is filling."),
       ("Kalpana", 4, "2026-10-26", "Biryani is fragrant and portions are large. Good for groups."))),

    ("naan-curry-hougang", "Naan & Curry House (Hougang)", "Indian", "North-East", "Hougang",
     "90 Hougang Ave 10, #02-01, Singapore 538766", 1.3708, 103.8932, "$$", 4.1, 1240,
     "North Indian restaurant with tandoori chicken, naan and rich curries.",
     ["naan", "tandoori", "biryani", "chicken curry"], ["naan", "tandoori"],
     hours("11:30", "22:00", ("mon",)),
     r(("Rakesh", 5, "2026-11-09", "Butter chicken with garlic naan is excellent. Tandoori is smoky."),
       ("Yasmin", 4, "2026-10-22", "Good North Indian in the heartlands. Portions are generous."))),

    ("biryani-pot-tampines", "Biryani Pot (Tampines)", "Indian", "East", "Tampines",
     "10 Tampines Central 1, #02-01, Singapore 529536", 1.3530, 103.9445, "$$", 4.2, 1520,
     "A biryani restaurant in Tampines serving dum biryani, tandoori and curries.",
     ["biryani", "tandoori", "naan", "chicken curry"], ["biryani", "naan"],
     hours("11:00", "22:00"),
     r(("Arif", 5, "2026-11-10", "Dum biryani is fragrant and the meat is tender. Worth the price."),
       ("Sangeeta", 4, "2026-10-23", "Naan is freshly baked. Gets busy at dinner."))),

    ("udon-ya-takashimaya", "Udon-Ya (Takashimaya)", "Japanese", "Central", "Orchard",
     "391 Orchard Rd, #B2-02, Singapore 238872", 1.3024, 103.8319, "$$", 4.1, 1260,
     "A Japanese noodle bar in Takashimaya with udon, tempura and rice bowls.",
     ["ramen", "sashimi", "unagi", "rice bowl"], ["ramen-bowl", "rice-bowl"],
     hours("10:30", "21:00"),
     r(("Tabitha", 4, "2026-11-08", "Tempura is light and crisp. Good quick lunch in the basement."),
       ("Jun Kai", 4, "2026-10-20", "Noodles have good bite. Seating is tight at lunch."))),
])


def main():
    with open(DATA, encoding="utf-8") as fh:
        data = json.load(fh)
    have = {e["id"] for e in data["eateries"]}
    pool = EAST + WEST + NORTH + NORTH_EAST + CENTRAL + CUISINE
    missing = [p for p in pool if p["id"] not in have]

    counts = {}
    for e in data["eateries"] + missing:
        counts[e["region"]] = counts.get(e["region"], 0) + 1
    print("regions:", {k: counts[k] for k in sorted(counts)}, "total", sum(counts.values()))

    if "--verify" in sys.argv:
        return 0
    if not missing:
        print("nothing to add")
        return 0

    data["eateries"].extend(missing)
    with open(DATA, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    print(f"added {len(missing)} · {len(data['eateries'])} total")
    return 0


if __name__ == "__main__":
    sys.exit(main())