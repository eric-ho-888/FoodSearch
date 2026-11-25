"""Contract checks for the Substrait deploy (no database, no external services)."""

import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import app  # noqa: E402


class ContractTests(unittest.TestCase):
    def test_app_data_has_no_database_usage(self):
        """The app is intentionally filesystem-only — no driver imports, no DB env."""
        with open(os.path.join(ROOT, "backend", "app.py"), encoding="utf-8") as fh:
            source = fh.read()
        for token in ("sqlite3", "psycopg", "asyncpg", "pymysql", "DATABASE_URL"):
            self.assertNotIn(token, source)

    def test_manifest_declares_no_database(self):
        path = os.path.join(ROOT, "substrait.yaml")
        if not os.path.exists(path):
            self.skipTest("substrait.yaml not present yet")
        with open(path, encoding="utf-8") as fh:
            manifest = fh.read()
        self.assertIsNone(re.search(r"^[[:space:]]*database[[:space:]]*:", manifest, re.M))

    def test_no_migrations_shipped(self):
        self.assertFalse(os.path.isdir(os.path.join(ROOT, "backend", "resources", "db", "migration")))

    def test_openapi_covers_registered_routes(self):
        path = os.path.join(ROOT, "openapi.json")
        if not os.path.exists(path):
            self.skipTest("openapi.json not present yet")
        with open(path, encoding="utf-8") as fh:
            spec = json.load(fh)
        self.assertIn("/health", spec["paths"])
        for route in ("/api/search", "/api/meta", "/api/eateries/{eatery_id}"):
            self.assertIn(route, spec["paths"])


if __name__ == "__main__":
    unittest.main()
