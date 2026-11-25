from urllib.parse import parse_qs, urlencode, urlsplit

from app import FoodSearchHandler


class handler(FoodSearchHandler):
    """Adapt Vercel's rewritten function URL back to the app's original route."""

    def _restore_original_path(self):
        parsed = urlsplit(self.path)
        if parsed.path != "/api/index":
            return

        query = parse_qs(parsed.query, keep_blank_values=True)
        original_path = query.pop("__path", ["/"])[-1]
        original_query = urlencode(query, doseq=True)
        self.path = original_path + (f"?{original_query}" if original_query else "")

    def do_GET(self):
        self._restore_original_path()
        super().do_GET()

    def do_HEAD(self):
        self._restore_original_path()
        super().do_HEAD()
