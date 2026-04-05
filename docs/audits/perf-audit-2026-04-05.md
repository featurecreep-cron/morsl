# Performance Audit Report — 2026-04-05

## Summary

| | Critical | High | Medium | Low |
|--|----------|------|--------|-----|
| **Found** | 3 | 5 | 3 | 0 |

- **Language/Framework**: Python 3.12 / FastAPI / PuLP (CBC solver)
- **Files Audited**: 9 / 43 source files (top 6 critical-path modules)
- **Scope**: broad
- **Focus**: all

---

## Findings

### [CRITICAL-1] Sequential per-filter HTTP round-trips in get_recipes() — `tandoor_api.py:178`

**Category**: I/O / Parallelism
**Hot path**: Every menu generation (single + weekly)
**Current**: `get_recipes()` loops over filter IDs sequentially. Each filter triggers a separate paginated HTTP fetch. With 5 filters, each paginating to 5 pages, that's 25 sequential round-trips.
**Call chain**:
```
MenuService.prepare_recipes() → TandoorAPI.get_recipes(filters=[...]) → for fid in filters: get_paged_results() → N pages × RTT
```
**Evidence**: Line 178 — `for fid in filters:` with `get_paged_results()` inside the loop body.
**Fix**: Fan out per-filter calls via `ThreadPoolExecutor.map()`. The requests.Session connection pool is already thread-safe. Reduces wall time from `O(K × pages × RTT)` to `O(max(pages) × RTT)` — ~5x for 5 filters.

---

### [CRITICAL-2] Per-profile TandoorAPI instances fragment the global cache — `weekly_generation_service.py:234`

**Category**: Caching / Architecture
**Hot path**: Weekly generation (multi-profile)
**Current**: `_prepare_profile_data()` constructs a new `MenuService` (and therefore a new `TandoorAPI` instance) for every profile. Then `_sync_generate()` constructs yet another for recipe detail fetching. The global `_api_cache` keys on `func.__qualname__ + args` — not on the instance — so cache hits work only when the exact same query params are used. Overlapping recipe pools across profiles miss the cache and hit Tandoor redundantly.
**Call chain**:
```
_sync_generate() → for profile in profiles: _prepare_profile_data() → MenuService(new TandoorAPI()) → prepare_data() → duplicate HTTP calls
```
**Evidence**: Line 234 creates a new MenuService per profile. Line 368 creates another TandoorAPI for detail fetching.
**Fix**: Pass a single shared TandoorAPI instance through to all MenuService instances and the detail-fetch call. The cache is already global and thread-safe — this is a construction discipline fix, not a cache refactor. Eliminates `(N-1)/N` redundant API calls for N profiles with overlapping recipe pools.

---

### [CRITICAL-3] Numrecipes backoff loop is the wrong infeasibility strategy — `solver.py:226`

**Category**: Algorithmic / Design
**Hot path**: Menu generation when constraints are tight (infeasible at requested count)
**Current**: `solve()` enters a `while True` loop. On each infeasible result, it decrements `numrecipes` by 1, rebuilds the entire LP from scratch, and re-solves. This is both expensive (O(R+C) per backoff step, up to `original_n - min_choices` iterations) and wrong from a UX perspective — the user asked for N recipes and silently gets fewer. Meanwhile, the soft constraint mechanism (weight > 0) already exists and handles infeasibility correctly: slack variables let the solver relax constraints while keeping the recipe count, and relaxed constraints are reported to the user.
**Call chain**:
```
solve() → while infeasible: numrecipes -= 1 → _build_problem() [O(R+C)] → _build_objective() [O(R)] → solver.solve()
```
**Evidence**: Lines 226-246 — the while loop decrements numrecipes and rebuilds. Soft constraints (lines 96-117) already handle relaxation for weight > 0.
**Fix**: Remove the numrecipes backoff loop. Instead, ensure all user-facing constraints use soft constraints (weight > 0) by default, so the solver always returns the requested recipe count and reports which constraints were relaxed. Hard constraints (weight=0) should be reserved for structural invariants (e.g., total count). This eliminates the rebuild loop entirely — single solve, always returns N recipes.

---

### [HIGH-1] Pagination follows `next` cursor serially — `tandoor_api.py:89`

**Category**: I/O / Pagination
**Hot path**: Any paginated Tandoor query (recipes, keywords, books)
**Current**: `get_paged_results()` fetches page 1, reads `next`, fetches page 2, reads `next`, etc. Strictly serial. Tandoor's DRF pagination returns `count` on page 1, so total pages are knowable after the first response.
**Fix**: After page 1, compute remaining pages and fetch all concurrently via ThreadPoolExecutor. Reduces N-page queries from N RTTs to 2 RTTs (page 1 serial + all remaining parallel).

---

### [HIGH-2] Cache key excludes instance identity — `tandoor_api.py:209` (utils.py)

**Category**: Caching / Correctness
**Hot path**: All cached TandoorAPI methods
**Current**: Cache key is `f"{func.__qualname__}|{args}"` — `self` is not part of the key. If two TandoorAPI instances point at different Tandoor servers (multi-profile deployment), they share cache entries. Instance A can receive Instance B's data.
**Fix**: Include a stable instance discriminator in the key (e.g., `id(self)` or a UUID assigned in `__init__`). One-line key change.
**Note**: Related to CRITICAL-2 — fixing CRITICAL-2 (shared instance) makes this less urgent, but it's still a correctness bug for any future multi-server scenario.

---

### [HIGH-3] get_book_recipes() silently truncates to first page — `tandoor_api.py:270`

**Category**: Pagination / Data Correctness
**Hot path**: Book-based constraints in menu generation
**Current**: `get_book_recipes()` calls `get_unpaged_results()` on `recipe-book-entry/`, which is a paginated DRF endpoint. If a book has more entries than the default page size, results are silently truncated. Recipes are dropped with no error or log.
**Fix**: Replace `get_unpaged_results()` with `get_paged_results()`. Data correctness fix — users with large recipe books get incomplete menus.

---

### [HIGH-4] Nested thread pool submissions risk contention — `recipe_detail_service.py:53,144`

**Category**: Concurrency / Deadlock Risk
**Hot path**: Recipe detail fetching after every generation
**Current**: `fetch_recipe_details()` submits one task per recipe to `_detail_pool` (max_workers=10). Each task calls `_batch_resolve_foods()`, which submits food-substitute lookups back to the *same* pool. With 5 recipes occupying 5 threads, the remaining 5 threads handle all inner food-substitute tasks. Under heavier load (10 recipes), inner tasks queue behind outer tasks that can't complete without inner results — throughput collapses.
**Fix**: Use a separate thread pool for food-substitute lookups, or flatten into a single-level `as_completed` pattern. Restores full parallelism.

---

### [HIGH-5] Sequential keyword/food tree fetches within constraints — `menu_service.py:166`

**Category**: I/O Pattern
**Hot path**: Constraint resolution during prepare_data()
**Current**: `_prepare_keyword_constraint()` loops over `item_ids` and calls `get_keyword_tree(kw_id)` serially. For a constraint with 4 keyword IDs, that's 4 sequential round-trips. Same pattern for food constraints.
**Fix**: Submit all tree-fetch calls to a thread pool and gather. Collapses N sequential round-trips to ~1.

---

### [MEDIUM-1] set(self.recipes) rebuilt on every constraint application — `solver.py:59`

**Category**: Algorithmic / Memory
**Hot path**: LP problem construction
**Current**: `_apply_constraint()` calls `set(self.recipes)` in both the `intersect_pool` and `exclude` branches. During `_build_problem()` replay, this allocates the same set C times. O(R * C) hash insertions.
**Fix**: Compute `self._recipe_set = set(self.recipes)` once in `__init__` and reference it. Zero allocations per constraint. Subsumed by CRITICAL-3 fix if backoff rebuild is eliminated, but still applies to first build.

---

### [MEDIUM-2] _prepare_makenow_constraint uses linear membership test — `menu_service.py:257`

**Category**: Algorithmic
**Hot path**: Makenow constraint resolution
**Current**: `[r for r in found if r in self.recipes]` — `self.recipes` is a list, so `r in self.recipes` is O(R) per element. O(|found| * R) total.
**Fix**: Build `self._recipe_set` once after `prepare_recipes()` completes. Membership test becomes O(1). Same fix as MEDIUM-1 in spirit — pre-compute a set.

---

### [MEDIUM-3] Cache timestamps dict grows unbounded — `utils.py`

**Category**: Memory Leak
**Hot path**: Long-running deployments
**Current**: `_api_cache` is an LRU with maxsize cap, but `_api_cache_timestamps` is a plain dict with no eviction. When LRU evicts an entry, its timestamp entry persists. Over weeks of operation with high query variety, the timestamps dict grows without bound.
**Fix**: Replace with `cachetools.TTLCache` which handles TTL natively, collapsing ~40 lines of manual cache management into ~5.

---

## Hot Path Map

| Operation | API Round-Trips | Thread Pool Submissions | Bottleneck |
|-----------|----------------|------------------------|------------|
| `POST /generate/{profile}` | 3-25 (filters + trees + pages) | 5-10 recipe details + 40-80 food subs | Sequential filter I/O |
| `POST /weekly-generation/{template}` | N × above (per profile, partially parallel) | Same × N profiles | Cache fragmentation + sequential solve |
| `GET /menu` | 0 (in-memory cache) | 0 | None |
| `GET /menu/stream` (SSE) | 0 | 0 | None |
| Proxy endpoints (`/recipe/{id}`, `/foods`, etc.) | 1-2 (cached) | 0 | Cache cold-start only |

## Priority Optimization Plan

1. **Fan out per-filter API calls** (CRITICAL-1) — biggest wall-time win, ~5x on multi-filter generations
2. **Share TandoorAPI instance across profiles** (CRITICAL-2) — eliminates redundant HTTP calls in weekly generation
3. **Fix nested thread pool** (HIGH-4) — prevents throughput collapse under load
4. **Parallelize keyword/food tree fetches** (HIGH-5) — collapses sequential constraint resolution
5. **Fix get_book_recipes() pagination** (HIGH-3) — data correctness, silent recipe truncation
6. **Remove numrecipes backoff, use soft constraints** (CRITICAL-3) — eliminates rebuild loop entirely, better UX
7. **Fix cache key identity** (HIGH-2) — correctness fix, lower urgency if CRITICAL-2 is fixed first
8. **Parallel pagination prefetch** (HIGH-1) — 2-3x on large recipe libraries
9. **Pre-compute recipe sets** (MEDIUM-1, MEDIUM-2) — O(1) membership, minor absolute impact
10. **Replace manual cache TTL with TTLCache** (MEDIUM-3) — memory hygiene for long-running deployments

## Files Not Audited

| File | Reason |
|------|--------|
| `routes/settings.py` (462 lines) | Admin-only, not hot path |
| `routes/proxy.py` (209 lines) | Thin async forwarding layer, bottleneck is upstream in tandoor_api.py |
| `order_service.py` (357 lines) | Same SSE pattern as generation, lower traffic |
| `scheduler_service.py` (276 lines) | APScheduler wrapper, not compute-intensive |
| `config_service.py` (261 lines) | YAML I/O, called once per generation |
| All other services | LOW priority per hot-path ranking |
| Frontend (`web/`) | Not analyzed (would need `/perf-audit --focus bundle`) |

