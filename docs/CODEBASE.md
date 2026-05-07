# Morsl Codebase Documentation

Feature-oriented documentation of morsl, a menu generation system for [Tandoor Recipes](https://tandoor.dev). Organized by what the user sees and does, with each section tracing from UI through API to backend logic.

**Tech stack:** Python 3.12 / FastAPI / PuLP (CBC solver) / Alpine.js / Vanilla CSS. Single Docker container, no database — JSON file persistence to a mounted volume.

**Deployment:** GHCR image (`ghcr.io/featurecreep-cron/morsl`). Configured via environment variables (`TANDOOR_URL`, `TANDOOR_TOKEN`) or the setup wizard's settings.json. Data lives in `data/` (profiles, settings, schedules, history, menus, templates, weekly plans).

---

## Table of Contents

1. [Setup & Onboarding](#1-setup--onboarding)
2. [Menu Generation & Viewing](#2-menu-generation--viewing)
3. [Recipe Detail & Rating](#3-recipe-detail--rating)
4. [Order System](#4-order-system)
5. [Shelf System](#5-shelf-system)
6. [Kiosk Mode & Security](#6-kiosk-mode--security)
7. [Profile Builder](#7-profile-builder)
8. [Weekly Planner](#8-weekly-planner)
9. [Scheduled Generation](#9-scheduled-generation)
10. [Theming & Branding](#10-theming--branding)
11. [Meal Plan Integration](#11-meal-plan-integration)
12. [PWA, QR Codes, Service Worker](#12-pwa-qr-codes-service-worker)
13. [Categories & Icon Mappings](#13-categories--icon-mappings)

**Appendices:**
- [A: Notable Patterns](#appendix-a-notable-patterns)
- [B: Code Organization](#appendix-b-code-organization)
- [C: API Reference](#appendix-c-api-reference)
- [D: Data Flow Diagrams](#appendix-d-data-flow-diagrams)

---

## 1. Setup & Onboarding

### User Experience

First-time users see a 6-step wizard that walks them from zero configuration to a working menu:

1. **Credentials** — Enter Tandoor URL and API token. Tests the connection before saving.
2. **Profile Selection** — Choose from 6 presets (Breakfast, Lunch, Dinner, Weekday Meals, Weekend Meals, Weeknight Dinners) or create custom-named profiles.
3. **Profile Configuration** — Multi-page constraint editor per profile (9 sub-pages: basics, keywords, ingredients, books, avoid, rating, freshness, new-recipes, review).
4. **Categories** — Create category groups (presets: "By Cuisine", "By Meal") or custom categories. Categories organize profiles into tabbed sections on the menu page.
5. **Assign Profiles to Categories** — Map each profile to a category.
6. **Done** — Redirects to the menu page.

The wizard is re-enterable: if credentials exist but no profiles, it starts at step 2. If everything exists, it redirects to `/admin`. The `?mode=add-profile` query parameter enters a single-profile-creation flow from the admin page.

### Frontend Implementation

`web/js/setup.js` — Single Alpine.js component `setupApp` registered via `Alpine.data()`.

State machine: `step` (1-6) controls which wizard page renders. `profileSubPage` navigates the 9-page profile editor within step 3. `profileQueue` holds all profiles being configured; `profileIndex` tracks which one is active.

Each search field (keywords, foods, books) has independent debounce timers and result arrays to prevent cross-contamination between simultaneous searches.

### API Calls Traced

| User Action | Frontend Call | Backend Route | Service |
|---|---|---|---|
| Test Connection | `POST /api/settings/test-connection` | `routes/settings.py` | httpx async probe to Tandoor `/api/food/?limit=1` |
| Save Credentials | `POST /api/settings/credentials` | `routes/settings.py` | `SettingsService.update()` — base64-encodes token, writes `settings.json` |
| Search Keywords | `GET /api/keywords?search=...` | `routes/proxy.py` | Proxies to Tandoor `GET /api/keyword/` |
| Search Foods | `GET /api/foods?search=...` | `routes/proxy.py` | Proxies to Tandoor `GET /api/food/` |
| Search Books | `GET /api/books?search=...` | `routes/proxy.py` | Proxies to Tandoor `GET /api/recipe-book/` |
| Create Profile | `POST /api/profiles` | `routes/profiles.py` | `ConfigService.create_profile()` — writes `data/profiles/{name}.json` |
| Create Category | `POST /api/categories` | `routes/categories.py` | `CategoryService.create()` — writes `data/categories.json` |
| Assign Category | `PATCH /api/profiles/{name}/category` | `routes/profiles.py` | `ConfigService.update_category()` |
| Setup Status | `GET /api/settings/setup-status` | `routes/settings.py` | Checks env vars + settings.json + profile count |

### Credential Resolution

Credentials follow a priority chain (`dependencies.py:resolve_credentials`):
1. Environment variables `TANDOOR_URL` + `TANDOOR_TOKEN` (highest priority)
2. `settings.json` fields `tandoor_url` + `tandoor_token_b64` (base64-decoded)
3. Raises HTTP 500 if neither source has both values

The test-connection and credentials endpoints use `require_admin_or_first_run` — allowing unauthenticated access during initial setup (no profiles exist), otherwise requiring admin auth.

---

## 2. Menu Generation & Viewing

### User Experience

The menu page (`/`) shows:
- **Category bar** at the top — tabbed sections grouping profiles
- **Profile buttons** within each category — tap to generate a new menu
- **Recipe carousel** — horizontal scrollable cards showing generated recipes with images, names, and keyword/food icons
- **Deck cards** below the carousel — tabs for switching between shelved generation results
- **Page dividers** in the carousel between generation batches ("Menu 1 of 3")

Generation shows a loading spinner (with customizable loading icon). On completion, recipes slide into view and the carousel scrolls to the start.

### Frontend Implementation

`web/js/app.js` — `menuApp()` function returns the Alpine.js component.

**State machine:** `state` field cycles through `loading → ready → generating → error`.

**Generation flow:**
1. User taps a profile button → `switchProfile(profileName)`
2. `POST /api/generate/{profile}` returns 202 (accepted)
3. `startStatusPolling()` polls `GET /api/status` every `STATUS_POLL_MS`
4. On `complete`, calls `loadMenuResult()` → `GET /api/menu`
5. `applyMenuData()` inserts recipes into the shelf system and updates the carousel

**Parallel path — SSE:** `connectMenuSSE()` opens `EventSource('/api/menu/stream')`. Events:
- `generating` — shows spinner on kiosk displays
- `menu_updated` — triggers debounced `loadMenu()` call
- `menu_cleared` — clears shelves on kiosk displays
- `connected` — reloads page if app version changed (new deployment)

SSE reconnects with exponential backoff (1s → 30s max).

### API Calls Traced

| Action | Endpoint | Route | Service | Result |
|---|---|---|---|---|
| Generate | `POST /api/generate/{profile}` | `routes/generation.py` | `GenerationService.start_generation()` | Returns 202, spawns async task |
| Poll Status | `GET /api/status` | `routes/menu.py` | `GenerationService.get_status()` | Returns `{state, started_at, error, ...}` |
| Fetch Menu | `GET /api/menu` | `routes/menu.py` | `GenerationService.get_current_menu()` | Returns cached menu from memory (loaded from `current_menu.json` on startup) |
| SSE Stream | `GET /api/menu/stream` | `routes/menu.py` | `GenerationService.subscribe()` | SSE event stream with keepalive |

### Generation Pipeline (backend)

`GenerationService.start_generation()` is async — it acquires an `asyncio.Lock`, sets state, then spawns `_sync_generate()` in a thread pool via `run_in_executor`. The sync method does all blocking work:

1. **MenuService** instantiated with profile config, Tandoor URL/token
2. `prepare_data()`:
   - `prepare_recipes()` — fetches recipe pool from Tandoor (all recipes, or filtered by params/filters/meal plan type). Deduplicates via `dict.fromkeys()`.
   - `prepare_constraints()` — fetches keyword trees, food data, book entries from Tandoor API. Multi-ID fetches use `ThreadPoolExecutor` for parallelism.
3. `select_recipes()`:
   - Creates `RecipePicker` (PuLP LP solver) with recipe pool and target count
   - Applies each constraint via type-specific handlers (keyword, food, book, rating, cookedon, createdon, makenow)
   - `solver.solve()` replays all constraint specs into a fresh LP problem (`_build_problem()`), builds objective (random coefficients for variety + soft constraint penalty via `_build_objective()`), then calls CBC solver
   - Returns `SolverResult` with selected recipes, relaxation info, warnings
4. `fetch_recipe_details()` — fetches full recipe data (images, ingredients, steps) for selected recipes
5. Result saved atomically to `data/current_menu.json`, cached in memory, SSE notification sent

---

## 3. Recipe Detail & Rating

### User Experience

Tapping a recipe card opens a modal showing:
- Recipe image (full width)
- Name, description, star rating (interactive)
- Ingredients list with amounts, units, foods
- Step-by-step instructions
- "Order" button (if orders enabled)
- Link to the recipe in Tandoor

Rating uses a name prompt if the `require_name_for_rating` setting is enabled. Ratings sync to Tandoor immediately.

### Frontend Implementation

**Menu page** (`app.js`): `openRecipe(recipe)` sets `selectedRecipe`, which triggers the modal template in `index.html`. `rateDrink(recipe, rating)` submits the rating (or `rateDrinkFromCard(recipe)` from the card view). If names are required, `showNamePrompt(recipe, 'rating', callback, rating)` shows the name prompt first.

**Admin page** (`admin.js`): Same modal pattern but with `openRecipe(recipe)` / `closeRecipe()`. Rating via `setRating(recipeId, rating)`.

### API Calls Traced

| Action | Endpoint | Route | Service |
|---|---|---|---|
| Get Recipe Detail | `GET /api/recipe/{id}` | `routes/proxy.py` | Proxies to Tandoor `GET /api/recipe/{id}` |
| Set Rating | `PATCH /api/recipe/{id}/rating` | `routes/proxy.py` | `PATCH` to Tandoor `/api/recipe/{id}/` with `{rating}` + `POST` to `/api/cook-log/` with rating and optional customer name |

---

## 4. Order System

### User Experience

When orders are enabled (`orders_enabled` setting), recipe cards show an "Order" button. Tapping it:
1. Optionally prompts for customer name (reusable name prompt with recent-names autocomplete from localStorage)
2. Submits the order
3. Shows a toast confirmation

On the admin side, the Orders tab shows:
- Per-recipe order counts
- Chronological order list with customer names and timestamps
- Real-time updates via SSE (new orders appear instantly)
- Ability to delete individual orders or clear all

### Frontend Implementation

**Menu page** (`app.js`): `orderDrink(recipe)` → optional `showNamePrompt()` → inline order submission via `POST /api/orders` (no separate `submitOrder` method). Stores recent names in localStorage (`recentNames`).

**Admin page** (`admin.js`): `connectOrderSSE()` opens `EventSource('/api/orders/stream')`. On `order` event, prepends to `orders` array and updates `orderCounts`. Exponential backoff reconnection on error.

### API Calls Traced

| Action | Endpoint | Route | Service |
|---|---|---|---|
| Place Order | `POST /api/orders` | `routes/orders.py` | `OrderService.place_order()` → creates Tandoor meal plan entry |
| List Orders | `GET /api/orders` | `routes/orders.py` | `OrderService.get_orders()` — merges Tandoor meal plans + server-stored orders |
| Order Counts | `GET /api/orders/counts` | `routes/orders.py` | `OrderService.get_order_counts()` |
| Delete Order | `DELETE /api/orders/{id}` | `routes/orders.py` | `OrderService.delete_order()` — routes to Tandoor or server store based on ID prefix |
| Clear Orders | `DELETE /api/orders` | `routes/orders.py` | `OrderService.clear_orders()` |
| SSE Stream | `GET /api/orders/stream` | `routes/orders.py` | `OrderService.subscribe()` — SSE with keepalive |

### Order Storage

Orders are primarily stored as **Tandoor meal plan entries** using a configured meal type (`order_meal_type_id`). This makes Tandoor the single source of truth with built-in history and calendar integration. A separate `store_and_notify` method provides server-side storage (`_server_orders`, capped at 1000) as an alternative code path, but the Tandoor write path does not automatically fall back to it on failure.

Order notes follow the format `"Ordered [by {name}] at HH:MM:SS"` — the timestamp is embedded in the note because Tandoor meal plans only store dates, not times. `_parse_customer_name()` and `_build_timestamp()` extract these fields when reading orders back.

---

## 5. Shelf System

### User Experience

Shelves provide multi-generation persistence. Each profile generation creates a "shelf" — a named tab that holds multiple generation batches. Users can:
- Tap deck cards below the carousel to switch between shelves
- See page dividers in the carousel between generation batches ("Menu 2 of 3")
- Long-press (touch) or right-click (desktop) a deck card to remove a shelf
- Generate into the same shelf repeatedly — new recipes prepend, old ones stay accessible

### Frontend Implementation

**Data structure** in `app.js`:
```
shelves: [{
    name: string,           // Profile name or "Menu"
    generations: [{
        recipes: Recipe[],
        generatedAt: string  // ISO timestamp
    }],
    currentIndex: number     // Always 0 (newest first)
}]
activeDeckName: string | null  // Currently visible shelf
```

**Key methods:**
- `addShelf(name, recipes)` — If shelf exists: prepends generation, caps at `MAX_SHELF_GENERATIONS`, moves to front. If new: creates and inserts at front.
- `removeShelf(name)` — Confirmation modal, then filters out. Switches active deck if needed.
- `mainCarouselRecipes` (computed) — Flattens active shelf's generations into a single array with divider objects between batches. Memoized via `_carouselCacheKey`.
- `flattenGenerations(generations, profile)` — Inserts `_isDivider: true` objects between generation batches for the carousel template.
- `loadShelves()` / `saveShelves()` — localStorage persistence at key `menu-shelves`.

**Long press handler** (`deckLongPress` object):
- `start(e, name)` — Sets 500ms timer. On fire, accesses Alpine component via `Alpine.$data(e.target)` and calls `removeShelf()`.
- `cancel()` — Clears timer on touchend/touchcancel.
- `_blockClick(e)` — Prevents click event from firing after long press completes.

**`clear_others` flag:** When a scheduled generation sets `clear_before_generate`, the menu JSON includes `clear_others: true`. On the frontend, `applyMenuData()` clears all shelves before adding the new generation, providing a fresh start without risking data loss if generation fails (the flag is only set post-success).

---

## 6. Kiosk Mode & Security

### User Experience

Kiosk mode transforms morsl into a customer-facing display (e.g., a tablet at a bar). When enabled:
- The menu page hides admin-access navigation
- A gesture (configurable: hamburger menu tap or long-press) triggers admin access
- PIN entry is required to reach the admin panel
- The admin panel shows a "Lock" button to return to the customer view

PIN protection works independently of kiosk mode — `admin_pin_enabled` protects the admin panel even without kiosk mode.

### Frontend Implementation

**Menu page** (`app.js`):
- `setupKioskGesture()` — Registers one of four gesture handlers: `'menu'` (hamburger tap, default), `'double-tap'` (double-click on header), `'long-press'` (2000ms pointer hold on header), or `'swipe-up'` (swipe from bottom 100px, distance > 150px). All trigger `kioskAdminAccess()`.
- `kioskAdminAccess()` — If PIN required: shows `showKioskPin` modal. If not: redirects to `/admin`.
- PIN modal: 4-digit numeric input, auto-submits on 4 digits, toggle visibility, error display.
- `submitKioskPin()` → `POST /api/settings/verify-pin` → on success, redirects to `/admin` with token in sessionStorage.

**Admin page** (`admin.js`):
- `_checkPinGate()` — On init, fetches `/api/settings/public` to check if PIN is required. Handles three cases:
  - `pin_timeout=0` (immediate): Always requires re-entry on page load
  - `pin_timeout>0` (timed): Checks client-side expiry of stored token
  - No PIN: Proceeds directly
- `adminFetch(url, opts)` — Wrapper around `fetch()` that attaches `X-Admin-Token` header from sessionStorage. On 401, shows PIN gate and aborts all in-flight requests.
- `submitPin()` → `POST /api/settings/verify-pin` → stores token + timestamp in sessionStorage → loads admin data.
- `lockKiosk()` — Clears token, redirects to `/`.

### Backend Security

**Token lifecycle** (`dependencies.py`):
- `create_admin_token()` — Generates `secrets.token_hex(16)`, stores with creation timestamp in `_admin_tokens` dict (thread-safe via `_admin_tokens_lock`).
- `require_admin` (FastAPI dependency) — Checks `X-Admin-Token` header against stored tokens. Token validity depends on `pin_timeout`:
  - `pin_timeout=0`: Valid for `PIN_IMMEDIATE_GRACE_SECONDS` (15s) — enough for admin page parallel API calls.
  - `pin_timeout>0`: Valid for that many seconds.
- `_cleanup_expired_tokens()` — Prunes tokens older than max TTL and enforces size limit (`ADMIN_TOKEN_CACHE_MAXSIZE=128`).
- `revoke_admin_tokens()` — Clears all tokens (called on PIN change).

**PIN verification** (`routes/settings.py`):
- Rate limiting: 5 attempts per IP per 60 seconds (429 on exceed)
- PIN hashing: `hash_pin()` and `verify_pin()` from `utils.py`
- Automatic migration from plaintext to hashed on first successful verification

---

## 7. Profile Builder

### User Experience

Profiles define what recipes appear in a menu generation. The profile builder exists in two places:

**Setup wizard** (step 3): A guided multi-page editor with 9 sub-pages:
- Basics (name, icon, recipe count)
- Keywords (theme keywords + balance keywords with per-keyword counts)
- Ingredients (include foods, with exceptions)
- Books (recipe collections)
- Avoid (exclude keywords, exclude foods)
- Rating (minimum star rating)
- Freshness (skip recently cooked recipes)
- New Recipes (include recently added recipes)
- Review (summary of all active rules)

**Admin panel** (Profiles tab): A full constraint editor with:
- Grouped constraints by type (keyword, food, book, rating, last-made, date-added, make-now)
- Collapsible constraint groups
- Add/remove/duplicate/reorder constraints
- Hard vs. soft constraint toggle per constraint
- Operator selection (at least, at most, exactly)
- Profile preview (shows matching recipe count without generating)
- Custom filter support (Tandoor saved filters)
- `show_on_menu` toggle, `item_noun` (e.g., "cocktail" instead of "recipe"), category assignment

### Frontend Implementation

**Setup wizard** (`setup.js`): Rules are stored in a nested object (`currentProfile.rules`) with named sections (`tagsInclude`, `foodsInclude`, `booksInclude`, `tagsExclude`, `foodsExclude`, `rating`, `avoidRecent`, `includeNew`). `buildConstraints(rules, choices)` converts this friendly format to the v2 constraints array for the API.

**Admin panel** (`admin.js`): Works directly with the v2 constraints array format. `profileEditor.constraints` is an array of constraint objects with `type`, `operator`, `count`, `items`, etc. Constraints are sorted by type for grouped display. The `expandedConstraint` index tracks which constraint card is open for editing.

### Profile Format (v2)

```json
{
    "name": "Dinner",
    "description": "Evening meals",
    "icon": "dinner",
    "category": "cat-uuid",
    "choices": 5,
    "min_choices": 3,
    "default": true,
    "show_on_menu": true,
    "item_noun": "recipe",
    "filters": [1, 2],
    "constraints": [
        {"type": "keyword", "items": [{"id": 5, "name": "Italian"}], "operator": ">=", "count": 2},
        {"type": "food", "items": [{"id": 10, "name": "Chicken"}], "except": [{"id": 11, "name": "Liver"}], "operator": ">=", "count": 1},
        {"type": "rating", "min": 4, "operator": ">=", "count": 1},
        {"type": "cookedon", "within_days": 14, "operator": "==", "count": 0},
        {"type": "createdon", "within_days": 30, "operator": ">=", "count": 1, "soft": true}
    ]
}
```

### API Calls Traced

| Action | Endpoint | Service |
|---|---|---|
| List Profiles | `GET /api/profiles` | `ConfigService.list_profiles()` |
| Get Profile | `GET /api/profiles/{name}` | `ConfigService.load_profile()` |
| Create Profile | `POST /api/profiles` | `ConfigService.create_profile()` |
| Update Profile | `PUT /api/profiles/{name}` | `ConfigService.update_profile()` |
| Delete Profile | `DELETE /api/profiles/{name}` | `ConfigService.delete_profile()` |
| Preview Profile | `POST /api/profiles/preview` | Creates MenuService, runs `prepare_data()`, returns recipe pool size |
| Set Category | `PATCH /api/profiles/{name}/category` | `ConfigService.update_category()` |

---

## 8. Weekly Planner

### User Experience

The Weekly tab in admin allows generating a full week of meals across multiple profiles:

1. **Create a template** — Define "slots": combinations of days, meal types, and profiles. Example: "Dinner → Dinner profile → Mon-Fri, 1 recipe/day" + "Brunch → Brunch profile → Sat-Sun, 2 recipes/day".
2. **Select template and week start date**
3. **Generate** — Runs each profile's generation for its assigned days. Progress shows per-profile status.
4. **Review** — See the generated plan organized by day and meal type.
5. **Regenerate slots** — Re-roll individual day/meal-type combinations.
6. **Save to Tandoor** — Creates meal plan entries in Tandoor for each recipe.

### Frontend Implementation

`admin.js` state:
- `templates` — Array of template definitions
- `templateEditor` — Current template being edited (name, description, deduplicate flag, slots array)
- `weeklyStatus` — Generation progress with `profile_progress` map
- `weeklyPlan` — Generated plan with `days` object keyed by date
- `weeklyPlanDays` (computed) — Sorted array of `{date, data}` for rendering

Template editor allows adding/removing slots, toggling days per slot, setting meal type and profile per slot, and recipes-per-day count.

### API Calls Traced

| Action | Endpoint | Service |
|---|---|---|
| List Templates | `GET /api/templates` | `TemplateService.list()` |
| Create Template | `POST /api/templates` | `TemplateService.create()` |
| Update Template | `PUT /api/templates/{name}` | `TemplateService.update()` |
| Delete Template | `DELETE /api/templates/{name}` | `TemplateService.delete()` |
| Generate Weekly | `POST /api/weekly/generate/{template}` | `WeeklyGenerationService.start_generation()` |
| Poll Status | `GET /api/weekly/status` | `WeeklyGenerationService.get_status()` |
| Get Plan | `GET /api/weekly/plan/{template}` | `WeeklyGenerationService.get_plan()` |
| Regenerate Slot | `POST /api/weekly/regenerate-slot` | Re-runs single profile generation for one day/meal |
| Save to Tandoor | `POST /api/weekly/save` | `MealPlanService.save_weekly_plan()` |
| Discard Plan | `DELETE /api/weekly/plan/{template}` | `WeeklyGenerationService.delete_plan()` |

### Backend Flow

`WeeklyGenerationService.start_generation()`:
1. Loads template definition from `TemplateService`
2. For each unique profile referenced in slots: runs `GenerationService._sync_generate()` (constraint solving)
3. Distributes selected recipes across days according to slot assignments
4. If `deduplicate` is true (default), ensures no recipe appears twice across the week
5. Saves plan to `data/weekly_plans/{template}.json`

---

## 9. Scheduled Generation

### User Experience

The Schedules section in admin settings allows automated menu generation:
- **Profile schedules** — Run a profile generation at specific days/times (e.g., "Dinner at 4 PM on weekdays")
- **Template schedules** — Run a weekly template generation (e.g., "Weekly Meal Plan every Sunday at 6 PM")
- Options per schedule: enable/disable, clear before generate, create meal plan in Tandoor, cleanup uncooked meal plans older than N days

### Frontend Implementation

`admin.js`: `scheduleForm` state object with `mode` (profile/template), cron day selection via `_selectedDays` array, and `buildCronDays()` / `parseCronDays()` for conversion to/from cron format (e.g., `"mon-fri"`, `"mon,wed,fri"`, `"*"`).

### API Calls Traced

| Action | Endpoint | Service |
|---|---|---|
| List | `GET /api/schedules` | `SchedulerService.list_schedules()` |
| Create | `POST /api/schedules` | `SchedulerService.create_schedule()` |
| Update | `PUT /api/schedules/{id}` | `SchedulerService.update_schedule()` |
| Delete | `DELETE /api/schedules/{id}` | `SchedulerService.delete_schedule()` |

### Backend Flow

`SchedulerService` wraps APScheduler's `AsyncIOScheduler` with `CronTrigger`.

**Startup** (`app/main.py:_setup_scheduler()`): Creates callback lambdas that bind the `settings` object, then passes them to the scheduler service. The scheduler loads persisted schedules from `data/schedules.json` and registers APScheduler jobs for each enabled schedule.

**Execution pipeline** (`_run_scheduled_generation()`):
1. **Pre-generate**: If `cleanup_uncooked_days > 0`, calls meal plan callback to delete old uncooked meal plans
2. **Generate**: For profile schedules, calls `_generation_callback(profile, clear_others=...)`. For template schedules, calls `_weekly_generation_callback(template_name, week_start)`.
3. **Post-generate**: If `create_meal_plan` is true, saves the menu to Tandoor as meal plan entries. For weekly templates, calls `_weekly_save_callback`.
4. Records `last_run` timestamp and persists schedules.

**Weekly schedule week calculation**: Calculates next Monday from today. If today is Monday, uses today.

---

## 10. Theming & Branding

### User Experience

**16 built-in themes** organized by family:
- **Material** (dark): Honey, Cast Iron (default), Ember
- **Glass** (dark): Espresso, Cobalt, Moss; (light): Sea Salt
- **Structured** (light): Porcelain, Terracotta, Pewter, Paprika
- **Soft** (light): Sage, Rhubarb, Fig, Sand, Basil

Each theme defines: label, accent color, mode (dark/light), family.

**Branding customization** (admin Branding tab):
- App name and taglines (header/footer slogans)
- Custom logo upload (SVG recommended — inherits theme color via `currentColor`)
- Custom favicon (with option to sync from logo)
- Custom loading icon (with option to sync from logo)
- Brand reset to defaults

### Frontend Implementation

**Theme registry** (`web/js/theme-registry.js`): `THEME_REGISTRY` object mapping theme keys to metadata. Each theme has a corresponding CSS file at `/css/theme-{name}.css`.

**Theme application** (`shared.js:applyThemeGlobal(name)`):
1. Sets `document.body.dataset.theme = name`
2. Swaps the `<link>` stylesheet href to the new theme CSS
3. Updates `meta[name="theme-color"]` for mobile browsers
4. Saves to localStorage (`morsl-theme`)

**SVG currentColor inheritance**: Brand SVGs use `currentColor` in their fill/stroke attributes. When inlined into the DOM via `inlineSvg()` (`shared.js`), they automatically adopt the theme's text color. This means a single SVG works across all 16 themes without modification.

**Branding uploads** (`admin.js`):
- `uploadBranding(type, event)` — FormData upload to `/api/settings/upload/{type}` (logo, favicon, loading-icon)
- `syncIconToLogo(type, checked)` — Downloads the logo blob and re-uploads as favicon/loading-icon
- `_updateBrandingPreviews()` — Inline renders all branding SVGs in the admin preview panels

### API Calls Traced

| Action | Endpoint | Service |
|---|---|---|
| Save Theme | `PUT /api/settings` with `{theme: name}` | `SettingsService.update()` |
| Upload Logo | `POST /api/settings/upload/logo` | Saves to `data/branding/`, updates settings |
| Upload Favicon | `POST /api/settings/upload/favicon` | Saves + regenerates icon sizes via `IconService` |
| Upload Loading Icon | `POST /api/settings/upload/loading-icon` | Saves to `data/branding/`, updates settings |
| Remove Branding | `DELETE /api/settings/{type}` | Removes file, resets setting |
| Reset All Branding | `POST /api/settings/branding/reset` | Clears all branding settings and files |

---

## 11. Meal Plan Integration

### User Experience

From the menu page, users can save the current menu to Tandoor as meal plan entries:
1. Tap the "Save to Meal Plan" button
2. Modal shows: date picker, meal type selector, user sharing, generation selector (which batch to save)
3. On save, creates one Tandoor meal plan entry per recipe

From the weekly planner, "Save to Tandoor" creates entries for all days/meals in the plan.

### Frontend Implementation

**Menu page** (`app.js`): `mealPlanSave` state object tracks modal visibility, selected date, meal type, users to share with, and which generation batch to save. `openMealPlanSave()` fetches meal types and users from Tandoor. `submitMealPlanSave()` sends the request.

### API Calls Traced

| Action | Endpoint | Service |
|---|---|---|
| Save Menu | `POST /api/meal-plan` | `MealPlanService.create_from_menu()` → creates entries via `TandoorAPI.create_meal_plans_from_menu()` |
| Save Weekly Plan | `POST /api/weekly/save` | `MealPlanService.save_weekly_plan()` |
| Get Meal Types | `GET /api/meal-types` | Proxies to Tandoor `GET /api/meal-type/` |
| Create Meal Type | `POST /api/meal-types` | `TandoorAPI.create_meal_type()` |
| Get Users | `GET /api/users` | Proxies to Tandoor user list |

### Tandoor Interaction

`MealPlanService` (and `TandoorAPI.create_meal_plans_from_menu()`) creates meal plan entries with:
- Recipe reference (id + name)
- Meal type (fetched as full object, not just ID — Tandoor API requires the full meal type object)
- Date (from_date = to_date = selected date)
- Shared users (array of `{id}` objects)
- Title = recipe name

---

## 12. PWA, QR Codes, Service Worker

### User Experience

Morsl installs as a Progressive Web App on mobile devices:
- "Add to Home Screen" prompt on supported browsers
- Offline-capable: serves cached static assets when the server is unreachable
- Custom app name from settings (dynamic `manifest.json`)

QR codes (optional, enabled via settings):
- Menu URL QR code — displayed in footer corner of the menu page
- WiFi QR code — standard `WIFI:T:WPA;S:ssid;P:password;;` format for guest WiFi

### Frontend Implementation

**Service Worker** (`web/service-worker.js`):
- Cache name: `morsl-v1`
- Install: Pre-caches static assets (HTML pages, CSS, JS, SVGs)
- Activate: Cleans old cache versions
- Fetch strategy:
  - API routes (`/api/*`): Network-only (never cached)
  - Admin paths: Network-only
  - Static assets: Network-first with cache fallback
  - Cacheable extensions: `.js`, `.css`, `.html`, `.png`, `.svg`, `.ico`, `.woff2`

**PWA Manifest** — Served dynamically at `/manifest.json` by `app/main.py:dynamic_manifest()`. Reads the base `web/manifest.json` and replaces `name`/`short_name` with the configured app name from settings.

**QR Codes** (`web/js/qrcode.min.js`):
- Admin: `renderQrPreviews()` renders previews for menu URL and WiFi QR in the settings tab
- Menu page: `_renderFooterQr()` renders corner QR codes when `qr_show_on_menu` is enabled
- WiFi QR string construction: `saveWifiQr()` builds the standard `WIFI:T:...;S:...;P:...;;` format

### Registration

`app.js:registerServiceWorker()` — Standard navigator.serviceWorker.register() call during init.

---

## 13. Categories & Icon Mappings

### User Experience

**Categories** organize profiles into tabbed sections on the menu page. Users see a horizontal category bar; tapping a category expands to show its profiles. Categories can be created in the setup wizard or managed in admin settings.

**Icon Mappings** let admins assign SVG icons to keywords and foods. When a recipe has a mapped keyword or food, its icon appears on the recipe card in the carousel.

### Frontend Implementation

**Categories** (`admin.js`):
- SortableJS integration for drag-and-drop reordering (`_initCategorySortable()`)
- CRUD operations with confirmation modals for deletes
- Category form with name, subtitle, and icon picker

**Icon Mappings** (`admin.js`):
- `iconMappings` object with `keyword_icons` and `food_icons` maps (name → icon key)
- Search-and-select for keyword/food names, icon picker for icon selection
- Auto-saves on add/remove

### API Calls Traced

| Action | Endpoint | Service |
|---|---|---|
| List Categories | `GET /api/categories` | `CategoryService.list()` |
| Create Category | `POST /api/categories` | `CategoryService.create()` |
| Update Category | `PUT /api/categories/{id}` | `CategoryService.update()` |
| Delete Category | `DELETE /api/categories/{id}` | `CategoryService.delete()` |
| Reorder | `PUT /api/categories/reorder` | `CategoryService.reorder()` |
| Get Mappings | `GET /api/icon-mappings` | `IconMappingService.get()` |
| Save Mappings | `PUT /api/icon-mappings` | `IconMappingService.save()` |

---

## Appendix A: Notable Patterns

### A1. Singleton Service Registry (not FastAPI's DI)

`dependencies.py` implements a manual singleton registry via `_get_or_create(key, factory)` and a module-level `_services: dict[str, object]` dict. Services are created once on first access and cached. This deviates from FastAPI's `Depends()` caching (which is per-request) because morsl needs cross-request singletons for SSE subscriber lists, in-memory caches, and running scheduler state.

FastAPI's `Depends()` signatures are still present on the factory functions (e.g., `get_generation_service(settings=Depends(get_settings))`) so they work as DI dependencies in route signatures, but the actual caching is done by the singleton registry, not by FastAPI.

`reset_credential_singletons()` and `reset_all_singletons()` allow selective or full cache clearing (used by credential updates and factory reset).

### A2. Frozen Dataclass Equality via ID

`models.py:TandoorEntity` is a frozen dataclass with `eq=False` that implements custom `__eq__` and `__hash__` based solely on `id`. All domain models inherit this. This means two `Recipe` objects with the same Tandoor ID are considered equal even if their other fields differ — critical for set operations in the constraint solver (deduplication, intersection).

The architecture test `TestFrozenDataclasses` enforces that all dataclasses are frozen unless explicitly allowlisted (only `GenerationStatus` and `WeeklyGenerationStatus` are mutable, as state machines).

### A3. LP Solver with Soft Constraint Relaxation

`solver.py:RecipePicker` uses PuLP's CBC solver with:
- **Binary decision variables** per recipe (selected or not)
- **Exact-count hard equality** — `lpSum(recipe_vars) == numrecipes` enforces that exactly the target number of recipes is selected (no range fallback; infeasible if constraints are too tight)
- **Hard constraints** added as LP equalities/inequalities
- **Soft constraints** use slack variables with penalty weights in the objective function. Weight derivation: `soft: true` maps to weight=1; an explicit `weight` field overrides. The `between` and `==` operators create two slack variables each, so a single soft constraint can produce multiple `RelaxedConstraint` entries.
- **Random coefficients** (`SOLVER_RANDOM_SCALE * random()` per recipe, scale=10) in the objective for variety — ensures different selections on each run. At default weights, variety contribution (~25 for a 5-recipe menu) dominates soft constraint penalties.
- **Constraint replay** — `_constraint_specs` stores all constraints as dicts. On `solve()`, the problem is rebuilt from scratch (`_build_problem()` replays all specs) because PuLP's `LpProblem` accumulates mutable state — without rebuild, calling `solve()` twice would corrupt the problem. Random coefficients are cached separately in `_random_coeffs` since the rebuild recreates all LP variables.
- **Relaxed constraint reporting** — After solving, any soft constraint with slack value > `SOLVER_SLACK_EPSILON` (1e-6) is reported in the result as a `RelaxedConstraint`.
- **Note:** `min_choices` is accepted in the profile config and passed to the solver but is currently unused (dead code).

### A4. SSE Publisher Mixin

`services/sse_publisher.py:SSEPublisher` is a mixin class (not a FastAPI dependency) that gives any service the ability to push events to SSE subscribers:
- Thread-safe subscriber management via `threading.Lock`
- Bounded queues (`maxsize=64`) per subscriber
- Automatic dead client cleanup: `put_nowait()` raises `QueueFull` for unresponsive clients, which triggers removal
- Used by `GenerationService` (menu events) and `OrderService` (order events)

### A5. JSON File Persistence

No database. All state persists as JSON files in `data/`:
- `settings.json` — App configuration
- `profiles/*.json` — Generation profiles
- `categories.json` — Category definitions and order
- `schedules.json` — Cron schedule definitions
- `current_menu.json` — Latest generated menu
- `history.json` — Generation history (capped at 100 entries)
- `templates/*.json` — Weekly plan templates
- `weekly_plans/*.json` — Generated weekly plans
- `icon_mappings.json` — Keyword/food → icon associations
- `custom_icons/` — Uploaded SVG files

Writes use `atomic_write_json()` (write to `.tmp`, then `os.replace()`) to prevent corruption on crash.

### A6. Architecture Tests as Lint

`tests/test_architecture.py` enforces structural constraints via AST parsing (not runtime):
- **Layer violations** — 4-tier hierarchy (Foundation → Core → Services → API). No upward imports.
- **`requests` containment** — Only `tandoor_api.py` may import `requests` (proxy.py uses `httpx`; the architecture test allowlists both files).
- **`httpx` containment** — Only settings route and proxy.
- **TandoorAPI instantiation** — Only in service modules, not routes.
- **Token exposure** — No f-strings containing "token" in logger calls.
- **Frozen dataclasses** — All dataclasses must be frozen (with explicit allowlist).
- **Sync core** — `solver.py`, `tandoor_api.py`, `models.py` must not import `asyncio`.
- **Broad except** — Requires explicit `# broad-except` comment.
- **No framework in services** — Services must not import FastAPI/Starlette.
- **No direct service construction in routes** — Must use DI.
- **No file writes in routes** — Must delegate to services.

### A7. Credential Priority Chain

Tandoor credentials resolve through a two-tier system:
1. **Environment variables** (`TANDOOR_URL` + `TANDOOR_TOKEN`) — Highest priority, typical for Docker deployment
2. **Settings JSON** (`tandoor_url` + `tandoor_token_b64`) — Set via setup wizard or admin UI. Token is base64-encoded for safe JSON storage.

Environment credentials are immutable from the UI. The setup status endpoint reports `has_env_credentials` so the admin UI can disable the credential editor.

### A8. Proxy Pattern for Tandoor API

`routes/proxy.py` provides a passthrough to the Tandoor API for operations that don't need morsl-side processing:
- Recipe details, keyword/food/book search, custom filters, meal types, users, ratings
- Uses the same credential resolution as other routes
- All endpoints use `httpx.AsyncClient` (module-level singleton with 10s timeouts) for async proxying — no `TandoorAPI` class involved
- Search/list endpoints (keywords, foods, books, custom-filters, users) require admin auth; read-only endpoints (recipe detail, meal types) are public
- Not a pure passthrough: the rating endpoint contains business logic (checks `ratings_enabled`/`save_ratings_to_tandoor` settings, creates cook log entries alongside the rating update)

### A9. TandoorAPI HTTP Configuration

`TandoorAPI.__init__` configures a `requests.Session` with:
- `HTTPAdapter` with `max_retries=2`, `backoff_factor=0.5`, retrying on `[502, 503, 504]`
- Connection pool: `pool_connections=5`, `pool_maxsize=10`
- Default timeout: `(5, 30)` seconds (connect, read)

Caching uses a `@cached` decorator backed by a global `cachetools.LRUCache` (maxsize=512, default TTL=240 minutes). Cache keys include `func.__qualname__`, `id(self)`, and stringified args. Thread-safe via `threading.Lock`. TTL of 0 bypasses caching.

`_unpack_list()` handles three Tandoor response shapes for forward-compatibility with Tandoor Next: raw list, single-page paginated envelope, and multi-page paginated envelope.

### A10. Thread-Safe Generation

Menu generation runs synchronously in a thread pool (`asyncio.run_in_executor(None, ...)`) because PuLP's CBC solver and the `requests`-based Tandoor API client are both blocking. The `GenerationService` wraps this with:
- `asyncio.Lock` to prevent concurrent generations
- State machine (`GenerationStatus` dataclass) tracking idle/generating/complete/error
- Atomic JSON writes for the menu file
- SSE notifications on state transitions

### A11. Menu Version Tracking

The generated menu includes a `version` field (hash or timestamp) that the frontend uses to detect staleness:
- `menuVersion` in `app.js` tracks the last-seen version
- `applyMenuData()` compares incoming version to detect new content
- SSE `connected` event includes the app version — if it differs from the frontend's `appVersion`, the page reloads (new deployment detected)

### A12. Admin Tier Progressive Disclosure

The admin UI has three tiers: essential, standard, advanced. Stored in localStorage (`admin-tier`). Tabs and sections are shown/hidden based on the selected tier:
- **Essential**: Generate, Profiles, Weekly, Settings
- **Standard**: Everything in essential (most settings visible)
- **Advanced**: Orders tab, Branding tab, all settings

### A13. Name Prompt Reuse

The name prompt modal on the menu page is shared between orders and ratings. The `namePrompt` state object includes: `show`, `name`, `callback`, `recipe`, `action` ('order' or 'rating'), `rating`, `confirmStep`. Recent names are stored in localStorage for autocomplete.

### A14. Debounced Search Pattern

All search inputs (keywords, foods, books) follow the same pattern:
1. Minimum character threshold (2 chars)
2. Debounce timer per search field (prevents API spam)
3. Independent result arrays per field (no cross-contamination)
4. Exclusion sets (already-selected items filtered from results)

### A15. Category Shelf Mapping

When a user taps a profile button in a category, the generated recipes are shelved under the profile name (not the category name). The `_targetShelf` variable captures the intended shelf name before generation starts, and `loadMenuResult()` uses it to place recipes in the correct shelf.

---

## Appendix B: Code Organization

### Layer Hierarchy

```
Layer 4 — API (HTTP boundary)
├── app/main.py              Lifespan, middleware, static file serving, page routes
├── app/api/routes/*.py      14 route modules (generation, menu, profiles, etc.)
├── app/api/dependencies.py  Singleton registry, auth, credential resolution
└── app/api/models.py        Pydantic request/response models

Layer 3 — Services (business logic)
└── services/*.py            16 service modules (stateless logic + persistence)

Layer 2 — Core (domain operations)
├── solver.py                LP formulation and constraint solving
└── tandoor_api.py           HTTP client for Tandoor REST API

Layer 1 — Foundation (shared primitives)
├── models.py                Frozen dataclasses (Recipe, Food, Keyword, etc.)
├── constants.py             Magic numbers, paths, factory defaults
├── utils.py                 Logging, date formatting, atomic file I/O, caching
└── app/config.py            Pydantic Settings (env var parsing)
```

### Frontend Structure

```
web/
├── index.html               Menu page (customer-facing)
├── admin.html               Admin panel
├── setup.html               Setup wizard
├── manifest.json            PWA manifest (base — name overridden dynamically)
├── service-worker.js        Offline caching
├── js/
│   ├── app.js               Menu page Alpine component (1381 lines)
│   ├── admin.js             Admin panel Alpine component (2608 lines)
│   ├── setup.js             Setup wizard Alpine component (892 lines)
│   ├── shared.js            SVG inlining, theme application, shared utilities
│   ├── constants.js         Frontend constants (localStorage keys, timing, limits)
│   ├── theme-registry.js    16 theme definitions
│   ├── icons.js             Built-in icon SVGs and lookup
│   ├── icon-picker.js       Icon picker modal component
│   └── qrcode.min.js        QR code generation library
├── css/
│   ├── theme-*.css          16 theme stylesheets
│   └── *.css                Component styles
└── icons/
    ├── default-favicon.svg  Stock favicon
    └── *.png                Generated icon sizes
```

### Frontend Architecture Notes

Each HTML page loads its own Alpine.js component function (`menuApp()`, `adminApp()`, `setupApp()`). These are monolithic — each file contains all state, methods, computed properties, and lifecycle hooks for its page. There is no component framework, build step, or module bundler.

Shared code lives in `shared.js` (SVG handling, theme application) and `constants.js` (timing constants, localStorage keys). `icons.js` provides icon lookup functions used by all three pages.

### Service Interdependencies

```
GenerationService → HistoryService, MenuService, RecipeDetailService, SSEPublisher
WeeklyGenerationService → TemplateService, ConfigService, GenerationService, SSEPublisher
SchedulerService → (callbacks from main.py bind all other services)
OrderService → TandoorAPI, SSEPublisher
MealPlanService → TandoorAPI
MenuService → TandoorAPI, RecipePicker (solver)
```

All service dependencies are injected at construction time via `dependencies.py` factory functions, not via FastAPI's `Depends()` at the route level. The exception is `MenuService`, which is instantiated fresh per generation (not a singleton) because it holds generation-specific state.

---

## Appendix C: API Reference

### Generation

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/generate/{profile}` | No | Generate menu from named profile (202) |
| POST | `/api/generate/custom` | Admin | Generate with inline constraints (202) |
| POST | `/api/generate` | No | Generate with default profile (202) |

### Menu & Status

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/menu` | No | Current generated menu |
| GET | `/api/menu/stream` | No | SSE stream for menu changes |
| DELETE | `/api/menu` | Admin | Clear current menu |
| GET | `/api/status` | No | Generation status |

### Profiles

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/profiles` | No | List all profiles (summary) |
| GET | `/api/profiles/{name}` | No | Full profile config |
| POST | `/api/profiles` | Admin | Create profile |
| PUT | `/api/profiles/{name}` | Admin | Update profile |
| DELETE | `/api/profiles/{name}` | Admin | Delete profile |
| POST | `/api/profiles/preview` | Admin | Preview matching recipe count |
| PATCH | `/api/profiles/{name}/category` | Admin | Set profile's category |

### Categories

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/categories` | No | List all categories (ordered) |
| POST | `/api/categories` | Admin | Create category |
| PUT | `/api/categories/{id}` | Admin | Update category |
| DELETE | `/api/categories/{id}` | Admin | Delete category |
| PUT | `/api/categories/reorder` | Admin | Reorder categories |

### Orders

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/orders` | No | Place order |
| GET | `/api/orders` | Admin | List orders (date range) |
| GET | `/api/orders/counts` | Admin | Per-recipe order counts |
| DELETE | `/api/orders/{id}` | Admin | Delete single order |
| DELETE | `/api/orders` | Admin | Clear all orders (date range) |
| GET | `/api/orders/stream` | Admin | SSE stream for new orders |

### Settings

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/settings` | Admin | All settings |
| PUT | `/api/settings` | Admin | Update settings (partial) |
| GET | `/api/settings/public` | No | Customer-visible settings subset |
| POST | `/api/settings/verify-pin` | No | Verify PIN, returns admin token |
| GET | `/api/settings/setup-status` | No | Setup completion status |
| POST | `/api/settings/test-connection` | Admin or First Run | Test Tandoor credentials |
| POST | `/api/settings/credentials` | Admin or First Run | Save Tandoor credentials |
| POST | `/api/settings/upload/logo` | Admin | Upload logo |
| DELETE | `/api/settings/logo` | Admin | Remove logo |
| POST | `/api/settings/upload/favicon` | Admin | Upload favicon |
| DELETE | `/api/settings/favicon` | Admin | Remove favicon |
| POST | `/api/settings/upload/loading-icon` | Admin | Upload loading icon |
| DELETE | `/api/settings/loading-icon` | Admin | Remove loading icon |
| POST | `/api/settings/branding/reset` | Admin | Reset all branding |
| POST | `/api/settings/factory-reset` | Admin | Full factory reset |

### Templates & Weekly Generation

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/templates` | Admin | List templates |
| POST | `/api/templates` | Admin | Create template |
| GET | `/api/templates/{name}` | Admin | Get template |
| PUT | `/api/templates/{name}` | Admin | Update template |
| DELETE | `/api/templates/{name}` | Admin | Delete template |
| POST | `/api/weekly/generate/{template}` | Admin | Start weekly generation (202) |
| GET | `/api/weekly/status` | Admin | Weekly generation status |
| GET | `/api/weekly/plan/{template}` | Admin | Get generated weekly plan |
| DELETE | `/api/weekly/plan/{template}` | Admin | Delete weekly plan |
| POST | `/api/weekly/regenerate-slot` | Admin | Regenerate single day/meal slot |
| POST | `/api/weekly/save` | Admin | Save weekly plan to Tandoor |

### Schedules

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/schedules` | Admin | List all schedules |
| POST | `/api/schedules` | Admin | Create schedule |
| PUT | `/api/schedules/{id}` | Admin | Update schedule |
| DELETE | `/api/schedules/{id}` | Admin | Delete schedule |

### History

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/history` | Admin | Paginated generation history |
| GET | `/api/history/{id}` | Admin | Single history entry |
| GET | `/api/history/analytics` | Admin | Constraint analytics |
| DELETE | `/api/history` | Admin | Clear all history |

### Proxy (Tandoor Passthrough)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/recipe/{id}` | No | Recipe details |
| PATCH | `/api/recipe/{id}/rating` | No | Set recipe rating + cook log |
| GET | `/api/keywords` | Admin | Search/list keywords |
| GET | `/api/foods` | Admin | Search foods |
| GET | `/api/foods/{id}` | Admin | Get food details |
| GET | `/api/books` | Admin | Search books |
| GET | `/api/custom-filters` | Admin | List Tandoor custom filters |
| GET | `/api/meal-types` | No | List meal types |
| POST | `/api/meal-types` | Admin | Create meal type |
| GET | `/api/users` | Admin | List Tandoor users |

### Meal Plan

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/meal-plan` | Admin | Save menu to Tandoor meal plan |

### Custom Icons

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/custom-icons` | No | List custom icons |
| POST | `/api/custom-icons` | Admin | Upload SVG icon |
| GET | `/api/custom-icons/all` | No | Get all icon SVGs |
| GET | `/api/custom-icons/{name}/svg` | No | Get single icon SVG |
| PATCH | `/api/custom-icons/{name}` | Admin | Rename icon |
| DELETE | `/api/custom-icons/{name}` | Admin | Delete icon |

### Icon Mappings

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/icon-mappings` | No | Get keyword/food → icon mappings |
| PUT | `/api/icon-mappings` | Admin | Update mappings |

### Health & Pages

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check (version, credentials, scheduler) |
| GET | `/` | No | Menu page (redirects to `/setup` if needed) |
| GET | `/admin` | No | Admin page (redirects to `/setup` if needed) |
| GET | `/setup` | No | Setup wizard (redirects to `/admin` if complete) |
| GET | `/manifest.json` | No | Dynamic PWA manifest |

---

## Appendix D: Data Flow Diagrams

### Menu Generation Flow

```
User taps Profile
    │
    ▼
POST /api/generate/{profile}                    [routes/generation.py]
    │
    ▼
GenerationService.start_generation()            [services/generation_service.py]
    │   ┌─ Rejects if state == GENERATING
    │   ├─ Sets state = GENERATING
    │   ├─ SSE: {type: "generating"}
    │   └─ Spawns asyncio Task
    │
    ▼ (in thread pool)
GenerationService._sync_generate()
    │
    ├─ MenuService(url, token, config)          [services/menu_service.py]
    │   ├─ prepare_recipes()
    │   │   └─ TandoorAPI.get_recipes()         [tandoor_api.py]
    │   │       └─ Paginated HTTP GET to Tandoor
    │   ├─ prepare_constraints()
    │   │   ├─ get_keyword_tree() / get_food() / get_book_recipes()
    │   │   └─ ThreadPoolExecutor for multi-ID fetches
    │   └─ select_recipes()
    │       └─ RecipePicker                     [solver.py]
    │           ├─ Build LP problem (binary vars, hard + soft constraints)
    │           ├─ Build objective (random coefficients + penalty)
    │           ├─ CBC solver
    │           └─ Return SolverResult
    │
    ├─ fetch_recipe_details()                   [services/recipe_detail_service.py]
    │   └─ TandoorAPI.get_recipe_details() per recipe
    │
    └─ Result dict {recipes, generated_at, status, ...}
    │
    ▼ (back in async context)
    ├─ atomic_write_json("current_menu.json")
    ├─ Update in-memory cache
    ├─ SSE: {type: "menu_updated"}
    ├─ Set state = COMPLETE
    └─ HistoryService.add_entry()
```

### Order Flow

```
Customer taps Order button
    │
    ├─ (Optional) Name prompt → recent names from localStorage
    │
    ▼
POST /api/orders {recipe_id, recipe_name, customer_name, servings}
    │                                           [routes/orders.py]
    ▼
OrderService.place_order()                      [services/order_service.py]
    │
    ├─ _get_meal_type(meal_type_id)  ─── Cached after first fetch
    │
    ├─ TandoorAPI.create_order_meal_plan()      [tandoor_api.py]
    │   └─ POST /api/meal-plan/ to Tandoor
    │       Note: "Ordered [by {name}] at HH:MM:SS"
    │
    ├─ Build order response {id, recipe_id, timestamp, ...}
    │
    └─ SSE: notify all order subscribers
            │
            ▼
        Admin page EventSource('/api/orders/stream')
            └─ Prepends to orders array, updates counts
```

### Scheduled Generation Flow

```
APScheduler CronTrigger fires
    │
    ▼
SchedulerService._run_scheduled_generation(schedule_id)
    │
    ├─ Pre-generate:
    │   └─ If cleanup_uncooked_days > 0:
    │       └─ meal_plan_callback("cleanup", {type, days})
    │           └─ TandoorAPI.cleanup_uncooked_meal_plans()
    │
    ├─ Generate (profile mode):
    │   └─ generation_callback(profile, clear_others=...)
    │       └─ _sched_generation() in main.py
    │           └─ GenerationService.start_generation() → wait_for_completion()
    │
    ├─ Generate (template mode):
    │   └─ weekly_generation_callback(template_name, week_start)
    │       └─ WeeklyGenerationService.start_generation()
    │
    ├─ Post-generate:
    │   └─ If create_meal_plan:
    │       ├─ Profile: meal_plan_callback("create", {type})
    │       └─ Template: weekly_save_callback(template_name)
    │           └─ MealPlanService.save_weekly_plan()
    │
    └─ Update schedule.last_run, persist schedules.json
```
