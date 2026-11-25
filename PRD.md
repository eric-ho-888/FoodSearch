# FoodSearch — Product Requirements Document

| | |
| --- | --- |
| **Product** | FoodSearch |
| **Version** | 1.0 |
| **Status** | Shipped to dev — <https://foodsearch.dev.sctp-dsai-2.apps.substrait.build> |
| **Owner** | eric-ho-888 |
| **Last updated** | 2026-11-25 |

---

## 1. Problem

Deciding where to eat nearby is slow. The information people actually need is
scattered: what a place serves, whether it is open *right now*, roughly how far
away it is, and whether other people rated it well. Generic map search returns
everything at once and says little about the food itself.

People also search by **dish**, not by restaurant. "Satay near me" is a natural
query that most directories handle poorly — they match business names, so a
hawker centre famous for satay may never surface.

## 2. Goal

A single, fast page that answers: **"What can I eat near me right now, and is
it good?"** — searchable by the dish a person has in mind, filterable by how far
they are willing to travel, and honest about when a place is open.

### Non-goals

- Not a booking, ordering or delivery product.
- Not a review-writing platform; it displays reviews, it does not collect them.
- Not a live commercial directory (see §7 Data policy).
- No user accounts, no personalisation, no server-side state.

## 3. Users

| Persona | Need | How FoodSearch helps |
| --- | --- | --- |
| **The craving searcher** — knows the dish, not the place | "Where do I get good mee rebus?" | Dish search ranked by specialty match, not business name |
| **The hungry commuter** — on the move, on a phone | "What's open near me, close by?" | Region tabs, Near me, Open now, one-thumb layout |
| **The planner** — choosing for a group or a trip | "Somewhere in the West, decent, open in the evening" | Region + category + open-now combined, hours table per listing |
| **The browser** — no specific dish | "Show me something good" | Categories, popular searches, rating sort |

Primary device is a **phone in the street**; second is a laptop planning a meal.
Both are first-class (see §6.4).

## 4. Scope — what shipped

### 4.1 Dish and cuisine search

Search must work on **what is served**, not just names.

- Matches dish names and cuisine: *satay, mee rebus, mee siam, nasi lemak,
  laksa, char kway teow, dim sum, chilli crab, roti prata, biryani, bibimbap,
  truffle fries*.
- Partial words (`prat`, `chic`) and multi-word dishes.
- Local spellings and colloquial names (`char kuay teow`, `sate`, `dosa`,
  `otak otak`, `mee pok`).
- **Typos**: one- or two-edit distance including transpositions (`lksa`,
  `chciken`, `bimbap`). Fuzzy matching is attempted **only when an exact search
  returns nothing**, and the UI says results are approximate — never silently
  substitute wrong food.
- Ranking: name and specialty matches outrank description text, then open-now,
  rating, and review count break ties.

### 4.2 Categories

Seven fixed cuisines: **Chinese, Malay, Indian, Western, Japanese, Korean,
Others**. Every category is populated.

### 4.3 Regions

Singapore's five planning regions as a tab bar directly in front of "Near me":
**Central, North, North-East, East and West**.

- Each tab shows how many places match the *current* search, so an empty region
  is visible before it is clicked.
- Regions combine with category, open-now and sorting.
- When a dish exists but not in the chosen region, the empty state names where
  it *is* available and offers a one-click "Search all regions".
- Regions live in the URL (`?region=West`) so they are linkable and survive
  reload and back/forward.

### 4.4 Opening hours

The most common cause of a wasted trip is a closed shop.

- Live badge per listing: "Open · closes 7:30 pm" or "Closed · opens 10:00 am
  tomorrow".
- Handles **overnight sessions** (`11:00–02:00`), **split services**
  (lunch `12:00–15:00` and dinner `18:00–23:00`), and **closed days**.
- Full weekly table on the detail page, today highlighted.
- All times Singapore time (SGT), evaluated server-side against the current time.
- "Open now" filter uses the same logic as the badge — they can never disagree.

### 4.5 Photos

Two photos per listing, bundled locally.

- Displayed on the card (first) and the detail page (both).
- Each photo carries **author, licence and source page**, shown under the image.
- No two listings share an image; packaging/shopfront shots are rejected in
  favour of plated dishes.

### 4.6 Reviews

- Top reviews per listing, sorted by rating then recency.
- Reviewer, date, star rating and text.
- A card shows the single strongest review to aid a quick decision.

### 4.7 Location and distance

- **Near me** uses browser geolocation (opt-in, never automatic).
- With a location, cards show distance ("480 m away", "1.1 km away") and
  "Nearest" sorting becomes meaningful.
- Without a location, "Nearest" still orders results from the city centre and
  the UI says so rather than silently pretending it knows where you are.

### 4.8 API

The same data is available as JSON for programmatic use:
`/api/search`, `/api/eateries/{id}`, `/api/meta`, `/health` — documented in
`openapi.json`.

## 5. Requirements summary

| ID | Requirement | Priority | Status |
| --- | --- | --- | --- |
| R1 | Search by specialty dish name | Must | Done |
| R2 | Seven cuisine categories, all populated | Must | Done |
| R3 | Opening hours with live open/closed status | Must | Done |
| R4 | Two photos per listing with attribution | Must | Done |
| R5 | Top reviews per listing | Must | Done |
| R6 | Five region tabs | Must | Done |
| R7 | Runs with no API and no database | Must | Done |
| R8 | Usable on phone and laptop | Must | Done |
| R9 | Typo tolerance without wrong-food substitution | Should | Done |
| R10 | Distance display and nearest sorting | Should | Done |
| R11 | Honest labelling of unconfirmed listings | Should | Done |
| R12 | JSON API | Could | Done |

## 6. Non-functional requirements

### 6.1 Constraints

- **No third-party APIs at runtime.** The dataset and photos are bundled.
- **No database.** Listings and images are read from files in the image; nothing
  is provisioned, migrated or backed up.
- **Standard library only** for the backend — no framework, no `pip install`.
- Deploy target: Substrait, serving `GET /health` on port 8000, API under `/api`.

### 6.2 Performance

- Page weight: photos ~5 MB total on disk, ~30 KB per image served, lazy-loaded;
  a listing card shows one image above the fold.
- Search executes in-process over an in-memory index — no network round trip.
- Live search debounced at 260 ms; results region swapped without a full reload.

### 6.3 Accessibility

- Semantic headings and landmarks; `role="tablist"`/`tab`/`aria-selected` on the
  region tabs with exactly one selected.
- `aria-live` on the result count so filter changes are announced.
- Focus-visible outlines on all interactive controls; no colour-only signalling
  (open/closed has text as well as colour).
- Respects `prefers-reduced-motion`.

### 6.4 Responsiveness

| Breakpoint | Behaviour |
| --- | --- |
| ≤ 560 px (phone) | Single-column cards; region tabs as a 3×2 grid; compact header; search field and button on one line |
| 561–860 px (tablet) | Two-column cards; full region row |
| ≥ 861 px (laptop/desktop) | Three-column cards; region tabs inline in the controls row |

Verified by rendering at 390, 768, 1280 and 1920 px.

### 6.5 Security

- All user input escaped before rendering; query capped at 120 characters.
- Static file serving rejects path traversal.
- Strict Content-Security-Policy, `nosniff`, and no inline script.
- Non-root user in the container; no secrets in the app.

## 7. Data policy

**The dataset is demo data, and the product says so.** Operating hours and
reviews are illustrative, not scraped. This is a deliberate constraint of the
no-API requirement, and it is disclosed on every page.

Each listing carries a `verified` flag:

- **66 confirmed** — the original curated set plus well-known Singapore venues
  (Maxwell, Chinatown Complex, Bedok 85, Changi Village, Clementi 448, Taman
  Jurong, Chomp Chomp and similar).
- **19 indicative** — real malls, chains or locations where the exact outlet is
  not confirmed. Labelled "Indicative listing" on the card, explained on the
  detail page.

**Closure audit.** Venues were checked for current status on 2026-11-25. Three
confirmed-closed venues were removed — JCube (closed Aug 2023), Tampopo at Liang
Court (demolished 2021) and The Grandstand at Turf City (vacated 2024) — along
with listings that could not be confirmed as real businesses. The audit is
recorded in `tools/verify_eateries.py` and enforced by tests so closed venues
cannot silently return.

**Known limitation.** "Confirmed" means the venue is known to exist, not that its
current operating status has been verified individually. Hours and reviews are
never authoritative. Moving to a real directory import is the correct next step
before any production use.

## 8. Success measures

| Measure | Target |
| --- | --- |
| Dish search finds a relevant top result for the 12 documented specialties | 12/12 |
| Region tabs all populated (no empty tab) | 5/5 |
| Test suite passing | 100% (45 tests) |
| Renders correctly at 390 / 768 / 1280 / 1920 px | 4/4 |
| Listings with two distinct photos | 100% |
| Closed venues remaining in dataset | 0 |

## 9. Out of scope / future

- Import from a real directory (CSV or licensed API) to replace demo data with
  verified listings, hours and reviews.
- Menu-level data and price ranges per dish.
- Saving favourites and sharing a shortlist.
- User-submitted reviews (requires accounts and moderation).
- A dedicated map view.

## 10. Decisions and rationale

| Decision | Why |
| --- | --- |
| Dish-first search, not name-first | Matches how people actually decide where to eat |
| Fuzzy matching only as a fallback, clearly flagged | Returning wrong food silently is worse than returning nothing |
| Regions as tabs, not a map | One-thumb operation on a phone; a map view was out of scope |
| No database | The requirement; the data is static and small enough to bundle |
| Photos bundled, not remote | No runtime API dependency; also guarantees attribution travels with the image |
| Indicative labelling instead of deletion | Keeps real locations useful without overstating certainty |
| Server-rendered HTML with progressive enhancement | Works without JavaScript; live search is an enhancement, not a requirement |