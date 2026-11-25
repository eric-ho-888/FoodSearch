#!/usr/bin/env python3
"""One-off: add eateries so every Singapore region has real coverage.

The original dataset was 25 Central / 4 East / 1 West / 0 North / 0 North-East,
which left three region tabs nearly empty. This adds well-known venues across
East, West, North and North-East. Listings are demo data (as the dataset note
says), with illustrative hours and reviews.

    python3 tools/add_region_eateries.py           # add what's missing
    python3 tools/add_region_eateries.py --verify  # report counts only
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "backend", "data", "eateries.json")

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def hours(open_, close, closed=()):
    return {day: ([] if day in closed else [[open_, close]]) for day in DAYS}


def review(spec):
    author, rating, date, text = spec.split("|", 3)
    return {"author": author, "rating": int(rating), "date": date, "text": text}


def place(sid, name, category, region, area, address, lat, lng, price, rating,
          review_count, description, specialties, photo_queries, open_hours, reviews):
    return {
        "id": sid, "name": name, "category": category, "region": region, "area": area,
        "address": address, "lat": lat, "lng": lng, "price": price, "rating": rating,
        "review_count": review_count, "description": description,
        "specialties": specialties, "photo_queries": photo_queries,
        "hours": open_hours, "reviews": [review(r) for r in reviews],
    }


NEW = [
    # ── East ────────────────────────────────────────────────────────────────
    place("fengshan-85-food-centre", "Bedok 85 Fengshan Food Centre", "Others", "East", "Bedok",
          "85 Bedok North St 4, Singapore 460085", 1.3327, 103.9385, "$", 4.3, 4890,
          "A Bedok supper institution: bak chor mee, satay and barbecue seafood under one noisy roof.",
          ["bak chor mee", "satay", "bbq seafood", "hokkien mee"], ["bak chor mee", "satay"],
          hours("16:00", "02:00"),
          ["Wei Ming|5|2026-11-14|Bak chor mee here is the reason to come. Go after 8pm when every stall is running.",
           "Farah|4|2026-10-27|Satay is well marinated and cheap. Seating is tight but turnover is fast."]),

    place("changi-village-hawker-centre", "Changi Village Hawker Centre", "Malay", "East", "Changi Village",
          "2 Changi Village Rd, Singapore 500002", 1.3892, 103.9864, "$", 4.2, 6120,
          "The place for nasi lemak by the sea, plus wanton mee and satay, a short walk from the ferry terminal.",
          ["nasi lemak", "wanton mee", "satay", "fried chicken"], ["nasi lemak", "satay"],
          hours("06:00", "23:00"),
          ["Nadia|5|2026-11-18|Came off the boat hungry and the nasi lemak delivered. Rice is properly coconutty.",
           "Jun Hao|4|2026-10-30|Long queue for the famous stall but it moves. Eat outside facing the water."]),

    place("east-coast-lagoon-food-village", "East Coast Lagoon Food Village", "Others", "East", "East Coast Park",
          "1220 East Coast Parkway, Singapore 468960", 1.3060, 103.9345, "$", 4.1, 7340,
          "Seaside hawker centre in East Coast Park, known for satay, otah and barbecue chicken wings at sunset.",
          ["satay", "otah", "bbq chicken wings", "grilled seafood"], ["chicken satay", "satay"],
          hours("11:00", "23:30"),
          ["Divya|4|2026-11-11|Satay with the sea breeze is hard to beat. Bring cash for most stalls.",
           "Terence|4|2026-10-22|Otah is freshly grilled and smoky. Parking fills up on weekend evenings."]),

    place("tampines-round-market", "Tampines Round Market & Food Centre", "Chinese", "East", "Tampines",
          "137 Tampines St 11, Singapore 521137", 1.3538, 103.9438, "$", 4.0, 3980,
          "A big heartland hawker centre with solid char kway teow, laksa and fish soup at breakfast time.",
          ["char kway teow", "laksa", "bak chor mee", "fish soup"], ["char kway teow", "laksa"],
          hours("06:00", "20:30", ("mon",)),
          ["Shuhui|4|2026-11-09|Char kway teow has good wok hei and the queue is reasonable before 9am.",
           "Bala|4|2026-10-25|Laksa is creamy without being cloying. Plenty of tables at mid-morning."]),

    place("alibabab-eating-house-katong", "Alibabab Eating House (Katong)", "Indian", "East", "Katong",
          "327 East Coast Rd, Singapore 428968", 1.3056, 103.9048, "$", 4.2, 2560,
          "A Katong prata house that runs late, with crisp roti prata, murtabak and teh tarik.",
          ["roti prata", "murtabak", "thosai", "teh tarik"], ["roti prata", "murtabak"],
          hours("07:00", "01:00"),
          ["Arun|5|2026-11-16|Prata is crisp at the edges and soft inside. Ask for extra curry.",
           "Michelle|4|2026-10-23|Murtabak is generous and the tea is properly strong. Good late-night stop."]),

    place("kim-choo-peranakan-katong", "Kim Choo Kueh Chang (Katong)", "Others", "East", "Katong / Joo Chiat",
          "109 East Coast Rd, Singapore 428800", 1.3053, 103.9034, "$", 4.3, 3110,
          "Peranakan rice dumplings, kueh and laksa in a shophouse on East Coast Road.",
          ["peranakan", "laksa", "rice dumpling", "kueh"], ["laksa", "mee siam"],
          hours("09:00", "20:00", ("mon",)),
          ["Grace|5|2026-11-07|Bak chang is properly wrapped and the laksa is the real deal. Lovely shophouse.",
           "Hock Seng|4|2026-10-20|Bought kueh to take home and they were gone by evening. Buy double."]),

    place("marine-parade-hawker-centre", "Marine Parade Hawker Centre", "Chinese", "East", "Marine Parade",
          "81 Marine Parade Central, Singapore 440081", 1.3026, 103.9055, "$", 4.0, 2870,
          "Neighbourhood hawker centre a step from the beach, strong on noodles and porridge in the morning.",
          ["bak chor mee", "wanton mee", "hokkien mee", "porridge"], ["bak chor mee", "hainanese chicken rice"],
          hours("06:30", "21:00"),
          ["Adeline|4|2026-11-05|Wanton mee is springy and the char siew is decent for the price.",
           "Kumar|4|2026-10-19|Quiet on weekday mornings, which is when I like it."]),

    place("siglap-upper-east-coast-food-centre", "Siglap Upper East Coast Food Centre", "Others", "East", "Siglap",
          "6 Upper East Coast Rd, Singapore 455200", 1.3130, 103.9256, "$", 4.1, 1980,
          "A compact East Coast food centre with satay, mee rebus and a popular popiah stall.",
          ["satay", "mee rebus", "popiah", "otah"], ["satay", "mee rebus"],
          hours("07:00", "22:00"),
          ["Natasha|4|2026-11-13|Mee rebus gravy is thick and the satay is freshly grilled. Good value.",
           "Iskandar|4|2026-10-28|Small place, big flavours. Go before noon for the popiah."]),

    # ── West ────────────────────────────────────────────────────────────────
    place("clementi-448-market", "Clementi 448 Market & Food Centre", "Chinese", "West", "Clementi",
          "448 Clementi Ave 3, Singapore 120448", 1.3149, 103.7652, "$", 4.1, 5210,
          "Clementi's busiest food centre: fish soup, char kway teow and cheap breakfast sets.",
          ["fish soup", "char kway teow", "bak chor mee", "laksa"], ["char kway teow", "laksa"],
          hours("06:00", "21:00"),
          ["Joanne|4|2026-11-15|Fish soup is clear and sweet. Queue is long but the stall is quick.",
           "Ravi|4|2026-10-24|Char kway teow here is properly smoky. Hard to find a seat at lunch."]),

    place("west-coast-market-square", "West Coast Market Square", "Chinese", "West", "West Coast",
          "69 West Coast Dr, Singapore 120069", 1.2933, 103.7695, "$", 4.0, 2640,
          "A west-side food centre near the market, with noodles, porridge and roast meats.",
          ["bak chor mee", "hokkien mee", "roast duck rice", "porridge"], ["bak chor mee", "hainanese chicken rice"],
          hours("06:30", "20:30"),
          ["Cheryl|4|2026-11-06|Roast duck rice is generous and well priced. Seating is easy off-peak.",
           "Mohan|4|2026-10-21|Solid everyday hawker food. The hokkien mee stall is the pick."]),

    place("jurong-west-505-market", "Jurong West 505 Market & Food Centre", "Malay", "West", "Jurong West",
          "Blk 505 Jurong West St 52, Singapore 640505", 1.3397, 103.6998, "$", 4.1, 3020,
          "A Jurong West market with nasi lemak, mee rebus and BBQ seafood stalls upstairs.",
          ["nasi lemak", "mee rebus", "satay", "otah"], ["nasi lemak", "mee rebus"],
          hours("06:00", "21:30"),
          ["Siti|5|2026-11-12|Nasi lemak is cheap and generous, and the sambal is properly spicy.",
           "Daryl|4|2026-10-26|Mee rebus is a solid bowl for the money. Gets busy on Sunday mornings."]),

    place("bukit-batok-155-market", "Bukit Batok 155 Market & Food Centre", "Chinese", "West", "Bukit Batok",
          "Blk 155 Bukit Batok St 11, Singapore 650155", 1.3490, 103.7495, "$", 4.0, 2210,
          "A neighbourhood food centre serving laksa, wanton mee and fish soup to the Bukit Batok crowd.",
          ["laksa", "wanton mee", "fish soup", "bak chor mee"], ["laksa", "bak chor mee"],
          hours("06:00", "20:00", ("sun",)),
          ["Hwee Ling|4|2026-11-04|Laksa is a good size and reasonably priced. Clean and airy for a hawker centre.",
           "Sam|4|2026-10-18|Wanton mee is the standout. Go early — the good stalls close by 2pm."]),

    place("choa-chu-kang-302-food-centre", "Choa Chu Kang 302 Food Centre", "Malay", "West", "Choa Chu Kang",
          "Blk 302 Choa Chu Kang Ave 4, Singapore 680302", 1.3853, 103.7443, "$", 4.1, 2460,
          "A heartland food centre with nasi padang, roti prata and mee goreng through the day.",
          ["nasi padang", "roti prata", "mee goreng", "nasi lemak"], ["nasi padang", "roti prata"],
          hours("06:30", "21:00"),
          ["Zul|5|2026-11-10|Nasi padang lauk is fresh and the prices are fair. Beef rendang is excellent.",
           "Bryan|4|2026-10-29|Prata is crisp and the curry is thick. Good breakfast spot in CCK."]),

    place("jurong-point-kopitiam", "Jurong Point Kopitiam", "Others", "West", "Jurong East",
          "1 Jurong West Central 2, #03-01, Singapore 648886", 1.3398, 103.7062, "$", 4.0, 1890,
          "A mall food hall in Jurong Point with chicken rice, noodles and roti prata under one roof.",
          ["chicken rice", "roti prata", "bak chor mee", "laksa"], ["hainanese chicken rice", "roti prata"],
          hours("08:00", "22:00"),
          ["Mabel|4|2026-11-08|Convenient when it rains. Chicken rice stall is reliable and quick.",
           "Arjun|4|2026-10-17|Not glamorous but everything is under one roof and air-conditioned."]),

    place("pandan-gardens-market", "Pandan Gardens Market & Food Centre", "Chinese", "West", "Pandan Gardens",
          "Blk 84 Pandan Gardens, Singapore 609645", 1.3148, 103.7490, "$", 4.0, 1640,
          "A quiet west-side market food centre, good for breakfast noodles and kaya toast.",
          ["bak chor mee", "kaya toast", "laksa", "wanton mee"], ["bak chor mee", "hainanese chicken rice"],
          hours("06:00", "20:00", ("mon",)),
          ["Serene|4|2026-11-03|Cheap and cheerful. Kaya toast set is my weekday breakfast.",
           "Patrick|4|2026-10-16|Very local, very quiet. The laksa stall is worth the walk."]),

    place("teban-gardens-market", "Teban Gardens Market & Food Centre", "Malay", "West", "Teban Gardens",
          "Blk 37 Teban Gardens Rd, Singapore 600037", 1.3192, 103.7428, "$", 4.0, 1420,
          "A small west-side market food centre with nasi lemak, mee rebus and fried bee hoon.",
          ["nasi lemak", "mee rebus", "fried bee hoon", "otah"], ["nasi lemak", "nasi padang"],
          hours("06:00", "20:00"),
          ["Hairul|4|2026-11-02|Nasi lemak is good value and the rice is fresh in the morning.",
           "Wendy|4|2026-10-15|Mee rebus is a comforting bowl. Seats are easy to find before 9am."]),

    place("grandstand-turf-city", "The Grandstand (Turf City)", "Western", "West", "Bukit Timah",
          "200 Turf Club Rd, Singapore 287994", 1.3416, 103.7916, "$$", 4.1, 2070,
          "A converted clubhouse with casual Western kitchens, coffee and weekend brunch spots.",
          ["brunch", "burger", "coffee", "pasta"], ["brunch cafe food", "french pasta"],
          hours("09:00", "22:00"),
          ["Evelyn|4|2026-11-14|Lots of parking and room for kids. Brunch plates are decent, coffee is good.",
           "Marcus|4|2026-10-27|Handy for the west but prices are mall-level. Good weekend option."]),

    # ── North ───────────────────────────────────────────────────────────────
    place("marsiling-mall-hawker-centre", "Marsiling Mall Hawker Centre", "Chinese", "North", "Marsiling",
          "4 Woodlands St 12, #02-01, Singapore 738623", 1.4324, 103.7795, "$", 4.0, 2380,
          "A tidy air-conditioned hawker centre in Marsiling with noodles, roast meats and dessert.",
          ["char kway teow", "roast duck rice", "bak chor mee", "chendol"], ["char kway teow", "bak chor mee"],
          hours("07:00", "21:30"),
          ["Liyana|4|2026-11-09|Air-conditioned hawker food is a win in the north. Char kway teow has good wok hei.",
           "Wei|4|2026-10-22|Clean, cheap and never too crowded on weekdays."]),

    place("woodlands-centre-road-food-centre", "Woodlands Centre Road Food Centre", "Malay", "North", "Woodlands",
          "Blk 4A Woodlands Centre Rd, Singapore 731004", 1.4370, 103.7860, "$", 4.1, 2740,
          "Woodlands' classic food centre by the checkpoint, known for nasi lemak and mee rebus.",
          ["nasi lemak", "mee rebus", "nasi padang", "otah"], ["nasi lemak", "mee rebus"],
          hours("06:00", "21:30"),
          ["Shafiq|5|2026-11-13|Nasi lemak is spot on and the queue moves fast before 8am.",
           "Irene|4|2026-10-25|Mee rebus is thick and sweet. Handy if you're heading across the border."]),

    place("yishun-925-chicken-rice", "Yishun 925 Hainanese Chicken Rice", "Chinese", "North", "Yishun",
          "Blk 925 Yishun Central 1, #01-249, Singapore 760925", 1.4301, 103.8351, "$", 4.3, 3410,
          "A Yishun coffee-shop stalwart serving silky chicken rice with a punchy chilli.",
          ["hainanese chicken rice", "roast chicken", "chicken rice"], ["hainanese chicken rice", "hainanese chicken rice"],
          hours("10:30", "20:30", ("mon",)),
          ["Jia Hui|5|2026-11-17|Chicken is silky and the rice is fragrant. Go before noon to avoid the queue.",
           "Alex|4|2026-10-26|Solid plate of chicken rice and the chilli is genuinely hot. Cheap too."]),

    place("chong-pang-market-food-centre", "Chong Pang Market & Food Centre", "Chinese", "North", "Yishun / Chong Pang",
          "Blk 104/105 Yishun Ring Rd, Singapore 760104", 1.4378, 103.8280, "$", 4.1, 3960,
          "The market food centre behind Chong Pang, busy from dawn with noodles, porridge and roast meats.",
          ["bak chor mee", "porridge", "roast duck rice", "hokkien mee"], ["bak chor mee", "hainanese chicken rice"],
          hours("06:00", "20:00"),
          ["Kelvin|4|2026-11-11|Roast duck rice is the one. Very busy on weekend mornings.",
           "Priya|4|2026-10-24|Good honest hawker breakfast. Prices are the lowest in the area."]),

    place("sembawang-hills-food-centre", "Sembawang Hills Food Centre", "Chinese", "North", "Upper Thomson",
          "590 Upper Thomson Rd, Singapore 574419", 1.3872, 103.8270, "$", 4.1, 2890,
          "A leafy food centre near Upper Thomson with char kway teow, carrot cake and fish soup.",
          ["char kway teow", "carrot cake", "fish soup", "laksa"], ["char kway teow", "laksa"],
          hours("06:30", "20:30", ("mon",)),
          ["Geraldine|4|2026-11-07|Carrot cake is crisp and generously portioned. Nice breezy setting.",
           "Hafeez|4|2026-10-20|Solid neighbourhood food centre. Fish soup is the pick of the stalls."]),

    place("admiralty-place-food-court", "Admiralty Place Food Court", "Others", "North", "Admiralty",
          "8 Woodlands Ave 7, #02-01, Singapore 738520", 1.4410, 103.7995, "$", 3.9, 1210,
          "A mall food court beside Admiralty MRT with mixed rice, noodles and Western plates.",
          ["mixed rice", "roti prata", "chicken rice", "western"], ["hainanese chicken rice", "roti prata"],
          hours("09:00", "21:30"),
          ["Brandon|4|2026-11-01|Convenient and cheap for a quick lunch near the MRT.",
           "Surekha|4|2026-10-14|Mixed rice stall has good variety. Nothing fancy, but reliable."]),

    place("khatib-bongsu-cafe", "Khatib Bongsu Waterside Cafe", "Western", "North", "Yishun",
          "Lower Seletar Reservoir Park, Yishun Ave 1, Singapore 769130", 1.4095, 103.8305, "$$", 4.0, 980,
          "A reservoir-side cafe with brunch plates, sandwiches and a view over the water.",
          ["brunch", "sandwich", "coffee", "cake"], ["sandwich-cafe", "pancakes-breakfast"],
          hours("09:00", "18:00", ("mon", "tue")),
          ["Charmaine|4|2026-11-10|Lovely spot for a slow morning. Sandwiches are fresh and coffee decent.",
           "Ridwan|4|2026-10-23|Breezy and quiet on weekdays. Limited menu but a nice walk after."]),

    place("yishun-park-nasi-lemak", "Yishun Park Nasi Lemak", "Malay", "North", "Yishun",
          "Blk 234 Yishun St 21, #01-01, Singapore 760234", 1.4280, 103.8401, "$", 4.2, 2210,
          "A neighbourhood nasi lemak stall with fried chicken wings, otah and a sweet-hot sambal.",
          ["nasi lemak", "fried chicken", "otah", "sambal"], ["nasi lemak", "nasi lemak"],
          hours("07:00", "21:00"),
          ["Aisyah|5|2026-11-15|The chicken wing is crisp and the sambal is the right kind of spicy.",
           "Chong|4|2026-10-28|Good value and quick service. Rice is fragrant even late in the day."]),

    # ── North-East ──────────────────────────────────────────────────────────
    place("hougang-105-hainanese-village", "Hougang 105 Hainanese Village Centre", "Chinese", "North-East", "Hougang",
          "Blk 105 Hougang Ave 1, Singapore 530105", 1.3670, 103.8890, "$", 4.2, 4620,
          "A Hougang market and food centre famous for carrot cake, char kway teow and fish soup.",
          ["carrot cake", "char kway teow", "fish soup", "bak chor mee"], ["char kway teow", "bak chor mee"],
          hours("06:00", "21:00"),
          ["Melody|5|2026-11-16|Carrot cake here is crispy, generous and nearly always sold out by lunch.",
           "Aziz|4|2026-10-27|Char kway teow is smoky and cheap. Go early on weekends."]),

    place("ang-mo-kio-628-market", "Ang Mo Kio 628 Market & Food Centre", "Chinese", "North-East", "Ang Mo Kio",
          "Blk 628 Ang Mo Kio Ave 4, Singapore 560628", 1.3700, 103.8447, "$", 4.1, 4380,
          "A big Ang Mo Kio food centre with satay, hokkien mee and roti prata across its stalls.",
          ["satay", "hokkien mee", "roti prata", "laksa"], ["satay", "roti prata"],
          hours("06:30", "22:00"),
          ["Wenjie|4|2026-11-12|Satay and hokkien mee both solid and cheap. Always a seat somewhere.",
           "Lavanya|4|2026-10-26|Roti prata stall does a proper crispy prata. Good breakfast stop."]),

    place("serangoon-garden-market", "Serangoon Garden Market & Food Centre", "Chinese", "North-East", "Serangoon Garden",
          "49A Serangoon Garden Way, Singapore 555945", 1.3648, 103.8652, "$", 4.2, 3720,
          "The daytime half of the Serangoon Garden food scene, strong on noodles and roast meats.",
          ["char kway teow", "roast duck rice", "bak chor mee", "wanton mee"], ["char kway teow", "bak chor mee"],
          hours("06:30", "20:00", ("mon",)),
          ["Shaun|4|2026-11-08|Roast duck rice is excellent for the price. Busy at breakfast.",
           "Yvonne|4|2026-10-21|Char kway teow is the standard-bearer here. Come before 11am."]),

    place("kovan-209-market", "Kovan 209 Market & Food Centre", "Others", "North-East", "Kovan",
          "Blk 209 Hougang St 21, Singapore 530209", 1.3595, 103.8883, "$", 4.1, 3140,
          "Kovan's market food centre with satay, mee siam and a well-loved fried kway teow stall.",
          ["satay", "mee siam", "char kway teow", "otah"], ["satay", "mee siam"],
          hours("06:30", "21:00"),
          ["Benedict|4|2026-11-09|Satay is properly charred and the peanut sauce is thick.",
           "Hana|4|2026-10-24|Mee siam is tangy and generous. Good variety for a small centre."]),

    place("punggol-settlement-food-court", "Punggol Settlement Food Court", "Others", "North-East", "Punggol",
          "3 Punggol Point Rd, Singapore 828694", 1.4108, 103.9108, "$", 3.9, 1560,
          "Food court at the end of Punggol Point, popular for a seafood dinner before a waterfront walk.",
          ["seafood", "satay", "chicken rice", "bbq seafood"], ["chilli crab Singapore", "chicken satay"],
          hours("11:30", "22:00"),
          ["Zhi Wei|4|2026-11-05|Handy stop after cycling. Seafood is fine and the view at dusk is the draw.",
           "Alethea|4|2026-10-19|Busy at weekends. Satay is decent and cheap."]),

    place("sengkang-square-food-hall", "Sengkang Square Food Hall", "Others", "North-East", "Sengkang",
          "10 Sengkang Square, #01-01, Singapore 544829", 1.3913, 103.8946, "$", 3.9, 1420,
          "A neighbourhood food hall beside Sengkang MRT with mixed rice, noodles and dessert stalls.",
          ["mixed rice", "noodles", "dessert", "chicken rice"], ["hainanese chicken rice", "mango-sago"],
          hours("08:00", "22:00"),
          ["Xin Yi|4|2026-10-30|Convenient and open late. Mixed rice stall is the best value.",
           "Joshua|4|2026-10-13|Nothing special but reliable, and dessert stall is good."]),

    place("upper-thomson-casuarina", "Casuarina Curry (Upper Thomson)", "Indian", "North-East", "Upper Thomson",
          "136 Casuarina Rd, Singapore 579759", 1.3906, 103.8319, "$", 4.3, 5230,
          "A prata institution on Casuarina Road: crisp roti prata, thosai and murtabak, open late.",
          ["roti prata", "thosai", "murtabak", "biryani"], ["roti prata", "thosai"],
          hours("07:00", "00:00"),
          ["Ashwin|5|2026-11-14|The reference point for prata in Singapore. Coin prata is worth the extra.",
           "Tracy|4|2026-10-25|Thosai is crisp and the sambar is good. Crowded on weekend mornings."]),
]


def main():
    with open(DATA, encoding="utf-8") as fh:
        data = json.load(fh)
    have = {e["id"] for e in data["eateries"]}
    missing = [p for p in NEW if p["id"] not in have]

    counts = {}
    for eatery in data["eateries"] + missing:
        counts[eatery["region"]] = counts.get(eatery["region"], 0) + 1
    print("current:", {k: counts[k] for k in sorted(counts)}, "total", sum(counts.values()))

    if "--verify" in sys.argv:
        return 0
    if not missing:
        print("nothing to add")
        return 0

    data["eateries"].extend(missing)
    with open(DATA, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    print(f"added {len(missing)} listings · {len(data['eateries'])} total")
    return 0


if __name__ == "__main__":
    sys.exit(main())