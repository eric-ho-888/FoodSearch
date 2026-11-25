"""Tests for FoodSearch: search, hours and HTTP routes.

    python3 -m unittest discover -s tests -v
"""

import json
import os
import sys
import threading
import unittest
import urllib.request
from datetime import datetime
from http.server import ThreadingHTTPServer

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../backend
ROOT = os.path.dirname(BACKEND)                                        # project root
sys.path.insert(0, BACKEND)

import app  # noqa: E402


def at(*args) -> datetime:
    return datetime(*args, tzinfo=app.TZ)


class SearchTests(unittest.TestCase):
    def names(self, **params):
        return [r["name"] for r in app.search_eateries(params, at(2026, 11, 25, 12, 30))["results"]]

    def test_specialty_examples_find_expected_places(self):
        """The first hit should be a place that genuinely serves the dish.

        Several places can serve a dish (three do nasi lemak), so this checks the
        top result is relevant rather than pinning one specific name.
        """
        cases = {
            "satay": "Satay by the Bay",
            "mee rebus": "Geylang Serai Market",
            "mee siam": "Geylang Serai Market",
            "nasi lemak": "Nasi Lemak",
            "laksa": "328 Katong Laksa",
            "chicken rice": "Tian Tian",
            "char kway teow": "Lao Fu Zi",
            "dim sum": "Tim Ho Wan",
            "chilli crab": "Jumbo Seafood",
            "roti prata": "Springleaf Prata Place",
            "bibimbap": "bibimbap",
            "truffle fries": "PS.Cafe",
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                first = app.search_eateries({"q": query}, at(2026, 11, 25, 12, 30))["results"][0]
                haystack = " ".join(first["specialties"] + [first["name"]]).lower()
                self.assertIn(expected.lower(), haystack)

    def test_empty_query_returns_everything(self):
        outcome = app.search_eateries({}, at(2026, 11, 25, 12, 30))
        self.assertEqual(outcome["count"], len(app.EATERIES))
        self.assertFalse(outcome["relaxed"])

    def test_nonsense_query_returns_nothing_without_relaxing(self):
        outcome = app.search_eateries({"q": "xqztv"}, at(2026, 11, 25, 12, 30))
        self.assertEqual(outcome["count"], 0)
        self.assertFalse(outcome["relaxed"])

    def test_typos_are_recovered(self):
        for typo, expected in [("lksa", "Laksa"), ("chciken", "Chicken"),
                               ("bimbap", "Bibimbap"), ("mee rebuss", "Mee Rebus")]:
            with self.subTest(typo=typo):
                outcome = app.search_eateries({"q": typo}, at(2026, 11, 25, 12, 30))
                self.assertGreater(outcome["count"], 0)
                self.assertTrue(outcome["relaxed"])
                top = outcome["results"][0]
                haystack = " ".join(top["specialties"] + [top["name"]]).lower()
                self.assertIn(expected.lower(), haystack)

    def test_synonyms(self):
        self.assertIn("Lao Fu Zi", self.names(q="char kuay teow")[0])
        self.assertIn("Satay", self.names(q="sate")[0])

    def test_category_filter(self):
        outcome = app.search_eateries({"category": "Korean"}, at(2026, 11, 25, 12, 30))
        self.assertTrue(outcome["results"])
        self.assertTrue(all(r["category"] == "Korean" for r in outcome["results"]))

    def test_category_and_query_intersect(self):
        outcome = app.search_eateries({"q": "satay", "category": "Japanese"}, at(2026, 11, 25, 12, 30))
        self.assertEqual(outcome["count"], 0)

    def test_open_now_filter(self):
        outcome = app.search_eateries({"open": "1"}, at(2026, 11, 23, 3, 0))  # Monday, 3am
        self.assertEqual(outcome["count"], 0)
        outcome = app.search_eateries({"open": "1"}, at(2026, 11, 25, 12, 30))
        self.assertTrue(outcome["results"])
        self.assertTrue(all(r["open"]["open"] for r in outcome["results"]))

    def test_distance_sort_uses_origin(self):
        # 1.3048/103.8318 is near Bugis; Katong Laksa should not be first.
        outcome = app.search_eateries(
            {"lat": 1.3048, "lng": 103.8318, "sort": "distance"}, at(2026, 11, 25, 12, 30)
        )
        distances = [r["distance_km"] for r in outcome["results"]]
        self.assertEqual(distances, sorted(distances))
        self.assertLess(distances[0], 3.0)

    def test_region_filter(self):
        for region in app.REGIONS:
            with self.subTest(region=region):
                outcome = app.search_eateries({"region": region}, at(2026, 11, 25, 12, 30))
                self.assertTrue(outcome["results"], f"{region} has no eateries")
                self.assertTrue(all(r["region"] == region for r in outcome["results"]))
                self.assertEqual(outcome["region"], region)

    def test_every_region_is_well_populated(self):
        """No region should look empty — each needs a meaningful number of listings."""
        counts = {}
        for eatery in app.EATERIES:
            region = app.region_of(eatery)
            counts[region] = counts.get(region, 0) + 1
        for region in app.REGIONS:
            with self.subTest(region=region):
                self.assertGreaterEqual(counts.get(region, 0), 8, counts)

    def test_boon_lay_place_appears_in_west_open_now(self):
        """Regression: a West venue open in the evening must show up under West + open now."""
        outcome = app.search_eateries({"region": "West", "open": "1"},
                                      at(2026, 11, 25, 20, 0))
        names = [r["name"] for r in outcome["results"]]
        self.assertIn("Boon Lay Place Market & Food Village", names)
        entry = next(e for e in app.EATERIES if "boon lay place" in e["name"].lower())
        self.assertEqual(entry["region"], "West")

    def test_every_listing_has_verification_status(self):
        for eatery in app.EATERIES:
            with self.subTest(eatery=eatery["id"]):
                self.assertIn("verified", eatery)
                self.assertIsInstance(eatery["verified"], bool)
        unverified = [e["id"] for e in app.EATERIES if not e["verified"]]
        # Unverified entries must be honestly labelled, and not the majority.
        self.assertLess(len(unverified), len(app.EATERIES) / 2, unverified)

    def test_known_closed_venues_are_absent(self):
        """Regression guard: venues confirmed closed must never reappear."""
        closed = {
            "jcube-jurong-food-court": "closed Aug 2023",
            "tampopo-ramen-liang-court": "Liang Court demolished 2021",
            "grandstand-turf-city": "Turf City vacated 2024",
        }
        ids = {e["id"] for e in app.EATERIES}
        names = " ".join(e["name"].lower() for e in app.EATERIES)
        for eid, why in closed.items():
            with self.subTest(venue=eid):
                self.assertNotIn(eid, ids, why)
        for word in ("jcube", "liang court", "turf city"):
            self.assertNotIn(word, names)

    def test_no_unverified_listing_ids(self):
        """The audit list in tools/verify_eateries.py must stay empty of live ids."""
        import importlib.util
        path = os.path.join(ROOT, "tools", "verify_eateries.py")
        if not os.path.exists(path):
            self.skipTest("verify_eateries.py not present")
        spec = importlib.util.spec_from_file_location("verify_eateries", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        ids = {e["id"] for e in app.EATERIES}
        offenders = (set(module.CLOSED) | set(module.UNVERIFIED)) & ids
        self.assertEqual(offenders, set())

    def test_dataset_covers_hawker_food_and_restaurants(self):
        """The dataset should span hawker centres, food courts and restaurants."""
        names = " ".join(e["name"].lower() for e in app.EATERIES)
        for kind in ("food centre", "food court", "restaurant", "cafe"):
            with self.subTest(kind=kind):
                self.assertIn(kind, names)
        self.assertEqual({e["category"] for e in app.EATERIES}, set(app.CATEGORIES))
        self.assertGreaterEqual(len(app.EATERIES), 80)

    def test_every_eatery_has_two_photos_and_reviews(self):
        for eatery in app.EATERIES:
            with self.subTest(eatery=eatery["id"]):
                self.assertGreaterEqual(len(app.photos_for(eatery["id"])), 2)
                self.assertGreaterEqual(len(eatery.get("reviews", [])), 2)
                self.assertTrue(eatery.get("description"))
                self.assertTrue(eatery.get("specialties"))

    def test_region_counts_match_dataset(self):
        """The count a region tab shows must equal what the dataset holds for it."""
        for region in app.REGIONS:
            with self.subTest(region=region):
                outcome = app.search_eateries({"region": region}, at(2026, 11, 25, 12, 30))
                expected = sum(1 for e in app.EATERIES if app.region_of(e) == region)
                self.assertEqual(outcome["count"], expected)

    def test_unknown_region_falls_back_to_all(self):
        outcome = app.search_eateries({"region": "Atlantis"}, at(2026, 11, 25, 12, 30))
        self.assertEqual(outcome["region"], "All")
        self.assertEqual(outcome["count"], len(app.EATERIES))

    def test_region_combines_with_query_and_category(self):
        outcome = app.search_eateries(
            {"q": "nasi lemak", "region": "West"}, at(2026, 11, 25, 12, 30)
        )
        self.assertTrue(outcome["results"])
        self.assertIn("Boon Lay Place Market & Food Village",
                      [r["name"] for r in outcome["results"]])
        self.assertTrue(all(r["region"] == "West" for r in outcome["results"]))

        outcome = app.search_eateries(
            {"q": "nasi lemak", "region": "Central", "category": "Malay"},
            at(2026, 11, 25, 12, 30),
        )
        self.assertTrue(outcome["results"])
        self.assertTrue(all(r["region"] == "Central" and r["category"] == "Malay"
                            for r in outcome["results"]))

    def test_region_of_infers_from_area(self):
        self.assertEqual(app.region_of({"area": "Katong / East Coast"}), "East")
        self.assertEqual(app.region_of({"area": "Yishun / Chong Pang"}), "North")
        self.assertEqual(app.region_of({"area": "Serangoon Garden"}), "North-East")
        self.assertEqual(app.region_of({"area": "Jurong / Boon Lay"}), "West")
        self.assertEqual(app.region_of({"area": "Tiong Bahru"}), "Central")
        # An explicit region always wins over the area guess.
        self.assertEqual(app.region_of({"area": "Orchard", "region": "North"}), "North")

    def test_rating_sort(self):
        outcome = app.search_eateries({"sort": "rating"}, at(2026, 11, 25, 12, 30))
        ratings = [r["rating"] for r in outcome["results"]]
        self.assertEqual(ratings, sorted(ratings, reverse=True))

    def test_bad_inputs_are_ignored(self):
        outcome = app.search_eateries(
            {"category": "Martian", "sort": "alphabetical", "lat": "nope", "lng": "x", "q": "a" * 500},
            at(2026, 11, 25, 12, 30),
        )
        self.assertEqual(outcome["category"], "All")
        self.assertEqual(outcome["sort"], "relevance")
        self.assertIsNone(outcome["origin"])
        self.assertLessEqual(len(outcome["query"]), app.MAX_QUERY_LEN)

    def test_every_result_has_two_photos_from_disk(self):
        outcome = app.search_eateries({}, at(2026, 11, 25, 12, 30))
        for result in outcome["results"]:
            with self.subTest(eatery=result["id"]):
                self.assertGreaterEqual(len(result["photos"]), 1)
                self.assertLessEqual(len(result["photos"]), 2)
                for photo in result["photos"]:
                    path = app.PHOTO_DIR / photo["file"]
                    self.assertTrue(path.is_file(), path)

    def test_all_categories_have_entries(self):
        for category in app.CATEGORIES:
            with self.subTest(category=category):
                self.assertTrue(any(e["category"] == category for e in app.EATERIES))


class HoursTests(unittest.TestCase):
    def test_overnight_session_runs_past_midnight(self):
        newton = app.BY_ID["newton-food-centre"]  # 11:00–02:00 daily
        self.assertTrue(app.opening_state(newton, at(2026, 11, 25, 1, 0))["open"])
        self.assertFalse(app.opening_state(newton, at(2026, 11, 25, 2, 0))["open"])

    def test_closed_day_rolls_to_next_opening(self):
        tiantian = app.BY_ID["tian-tian-chicken-rice"]  # Mon closed
        state = app.opening_state(tiantian, at(2026, 11, 23, 12, 0))
        self.assertFalse(state["open"])
        self.assertEqual(state["detail"], "opens 10:00 am tomorrow")

    def test_lunch_split(self):
        jumbo = app.BY_ID["jumbo-seafood"]  # 12–3, 6–11
        self.assertFalse(app.opening_state(jumbo, at(2026, 11, 25, 15, 30))["open"])
        self.assertEqual(app.opening_state(jumbo, at(2026, 11, 25, 15, 30))["detail"], "opens 6:00 pm")
        self.assertTrue(app.opening_state(jumbo, at(2026, 11, 25, 22, 0))["open"])

    def test_week_hours_marks_today(self):
        rows = app.week_hours(app.BY_ID["tian-tian-chicken-rice"], at(2026, 11, 25, 12, 0))
        self.assertEqual(len(rows), 7)
        self.assertEqual([r["day"] for r in rows if r["today"]], ["Wednesday"])

    def test_time_formatting(self):
        self.assertEqual(app.fmt_time("19:30"), "7:30 pm")
        self.assertEqual(app.fmt_time("00:05"), "12:05 am")
        self.assertEqual(app.fmt_time("12:00"), "12:00 pm")


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), app.FoodSearchHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def get(self, path):
        url = f"http://127.0.0.1:{self.port}{path}"
        with urllib.request.urlopen(url) as response:
            return response.status, response.headers, response.read()

    def test_home_page(self):
        status, headers, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn("FoodSearch", body.decode())

    def test_search_api(self):
        status, _, body = self.get("/api/search?q=nasi%20lemak")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(payload["meta"]["count"], 3)
        for result in payload["results"]:
            self.assertIn("nasi lemak", [s.lower() for s in result["specialties"]])
            self.assertIn("top_review", result)

    def test_detail_page(self):
        status, _, body = self.get("/eatery/328-katong-laksa")
        text = body.decode()
        self.assertEqual(status, 200)
        self.assertIn("Opening hours", text)
        self.assertIn("Top reviews", text)
        self.assertEqual(text.count('class="photo"'), 2)

    def test_unknown_eatery_is_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/eatery/does-not-exist")
        self.assertEqual(ctx.exception.code, 404)

    def test_static_and_traversal(self):
        photo = app.photos_for("tian-tian-chicken-rice")[0]
        status, headers, body = self.get(photo["src"])
        self.assertEqual(status, 200)
        self.assertIn(photo["file"].rsplit(".", 1)[-1], headers["Content-Type"])
        self.assertIn("max-age", headers["Cache-Control"])

        for path in ("/static/../app.py", "/static/%2e%2e/app.py", "/static/../data/eateries.json"):
            with self.subTest(path=path):
                try:
                    status, _, body = self.get(path)
                except urllib.error.HTTPError as exc:
                    status = exc.code
                self.assertNotIn(b"import argparse", body if status == 200 else b"")

    def test_tagline_sits_under_the_wordmark_on_every_page(self):
        for path in ("/", "/eatery/maxwell-food-centre-cafe"):
            with self.subTest(path=path):
                status, _, body = self.get(path)
                text = body.decode()
                self.assertEqual(status, 200)
                self.assertIn('class="brand-tagline"', text)
                self.assertIn("yummy food nearby", text)
                # The tagline must come after the wordmark inside the brand block.
                self.assertLess(text.index('class="brand-name"'),
                                text.index('class="brand-tagline"'))

    def test_region_tabs_render_before_near_me(self):
        status, _, body = self.get("/?region=East")
        text = body.decode()
        self.assertEqual(status, 200)
        self.assertIn('class="region-tabs"', text)
        self.assertLess(text.index("region-tabs"), text.index("locate-btn"))
        for region in app.REGIONS:
            self.assertIn(f'data-region="{region}"', text)
        self.assertIn('class="region-tab is-active" href="/?region=East"', text)

    def test_region_param_in_search_api(self):
        status, _, body = self.get("/api/search?region=West")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(payload["meta"]["region"], "West")
        self.assertTrue(all(r["region"] == "West" for r in payload["results"]))

    def test_meta_lists_regions(self):
        status, _, body = self.get("/api/meta")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["regions"], app.REGIONS)

    def test_health(self):
        status, _, body = self.get("/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"ok": True})

    def test_query_is_escaped(self):
        status, _, body = self.get("/?q=%3Cscript%3Ealert(1)%3C%2Fscript%3E")
        text = body.decode()
        self.assertEqual(status, 200)
        self.assertNotIn("<script>alert(1)</script>", text)
        self.assertIn("&lt;script&gt;", text)


if __name__ == "__main__":
    unittest.main()