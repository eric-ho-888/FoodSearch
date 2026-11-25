# FoodSearch

Find nearby food in Singapore. Search by dish or cuisine, filter by category,
see opening hours at a glance, and browse two photos plus the top reviews for
each place.

Built with the Python standard library only — **no frameworks, no API keys, no
network calls at runtime**. The dataset and photos ship with the app.

## Run it

```bash
cd backend
python3 app.py                 # http://localhost:8000
python3 app.py --open          # ...and open it in your browser
python3 app.py --port 9000     # different port (it will step forward if busy)
python3 app.py --host 0.0.0.0  # reachable from a phone on the same Wi-Fi
```

Deployed, it runs in a container: `HOST=0.0.0.0`, `PORT` from the environment, and
`--single-port` so it never drifts off the probed port.

Nothing to install. Requires Python 3.9+.

## What's inside

| Path | Purpose |
| --- | --- |
| `backend/app.py` | The whole app: data loading, search, hours logic, HTML rendering, HTTP server |
| `backend/data/eateries.json` | 85 Singapore eateries across 7 categories and 5 regions (66 confirmed, 19 indicative) |
| `backend/static/app.css`, `app.js` | Styling and live-search enhancement |
| `backend/static/photos/` | Two bundled WebP dish photos per eatery (~5 MB total), plus `manifest.json` with credit/licence data |
| `backend/tests/` | Search, hours, HTTP and deploy-contract tests |
| `cicd/Dockerfile.backend` | Container image: Python 3.12 slim, non-root, `GET /health` on 8000 |
| `substrait.yaml` | App description for the platform (no database, no services) |
| `openapi.json` | The app's published API description |
| `tools/fetch_photos.py` | Rebuilds the photo bundle from Wikimedia Commons (stdlib only) |
| `tools/repick_photos.py` | Re-assigns photos so no image is reused across listings |
| `tools/add_region_eateries.py` | One-off seed that gave every region real coverage |
| `tools/expand_eateries.py` | Seed that added coffee shops and restaurants across all regions |
| `tools/verify_eateries.py` | Audit list of closed/unverified venues; removes them from the dataset |
| `tools/fetch_commons_candidates.py` | Builds a pool of candidate photos per dish from Commons search |

There is **no database**: listings and photos ship inside the image and the app only
reads them, so the deploy declares no `database:` and ships no migrations.

## Features

**Categories** — Chinese, Malay, Indian, Western, Japanese, Korean, Others.

**Regions** — a tab bar in front of "Near me" for Singapore's planning regions:
Central, North, North-East, East and West. Each tab shows how many places match
your current search, and regions combine with the category and "Open now" filters.

**Search** works on dish names and cuisine, so specialties like *satay*, *mee
rebus*, *mee siam*, *nasi lemak*, *laksa*, *char kway teow*, *dim sum*, *chilli
crab*, *roti prata*, *biryani*, *bibimbap* and *truffle fries* all find the right
place. It also:

- matches partial words (`prat`, `chic`) and multi-word dish names;
- recovers from typos and transpositions (`lksa`, `chciken`, `bimbap`) by
  widening to fuzzy matches only when an exact search finds nothing, and says so;
- knows local spellings (`char kuay teow`, `sate`, `dosa`, `otak otak`);
- ranks name and specialty matches above description text, then breaks ties by
  open-now status, rating and review count.

**Filters** — category chips, an "Open now" toggle, and sorting by best match,
nearest or top rated.

**Near me** — uses the browser's geolocation; with a location, every card shows
the distance and distance sorting works.

**Opening hours** — each listing shows today's hours, a live open/closed badge
("Open · closes 7:30 pm", "Closed · opens 10:00 am tomorrow"), and a full weekly
table on the detail page. Overnight sessions (`11:00–02:00`), split lunch/dinner
sessions and closed days are handled. All times are Singapore time (SGT).

**Detail page** — description, specialties, two credited photos, the full week's
hours, and top reviews sorted by rating then recency, with a Maps link.

## API

The UI uses these, and they're handy on their own:

```
GET /api/search?q=satay&category=Malay&region=East&open=1&sort=distance&lat=1.29&lng=103.85
GET /api/eateries/328-katong-laksa     # one listing, with its full weekly hours
GET /api/meta
GET /health
```

`/api/search` returns `meta` (filters applied, count, whether results were
typo-relaxed, server time) and `results` (full listing data, photos with
attribution, open state, top review, optional distance).

## Data and photos

Listings, hours and reviews are **demo data** for demonstration, not a live
directory — confirm details before visiting.

Venues were checked for status on 2026-11-25. Three that had closed were removed
(JCube, Tampopo at Liang Court, The Grandstand at Turf City), along with listings
that could not be confirmed as real businesses — an earlier expansion had
generated some from memory. `tools/verify_eateries.py` records that audit and
`tests/test_app.py` guards against those venues returning.

Each listing carries a `verified` flag. **66 are confirmed venues**; **19 are
indicative** — real malls, chains or locations where the exact outlet is not
confirmed. The app labels those "Indicative listing" on the card and explains it
on the detail page, so nothing is presented as more certain than it is.

Photos are Creative Commons images from Wikimedia Commons. Each photo's author,
licence and source page are stored in `static/photos/manifest.json` and shown
under the photo on the detail page.

To rebuild the photo bundle:

```bash
python3 tools/fetch_photos.py            # fetch anything missing
python3 tools/fetch_photos.py --verify   # report coverage only
python3 tools/repick_photos.py --verify  # check for reused photos
```

## Tests

```bash
cd backend
python3 -m unittest discover -s tests -v
```