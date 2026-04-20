# Stack Migration: Vue 3 + SQLite

Status: **design** — approved, not started

## Context

morsl is architecturally single-tenant. Every layer — JSON file persistence, global service singletons, monolithic Alpine.js frontend — assumes one user, one instance. Phase 2 features (template builder, candidate selection, curation state, shopping list integration) require a stack that supports multi-user SaaS. Building Phase 2 on the current stack means building it twice.

**Decision:** Refactor stack before building Phase 2 features.

## Current stack

| Layer | Technology | Lines |
|-------|-----------|-------|
| Backend framework | FastAPI + Uvicorn | keeps |
| Solver | PuLP/CBC | keeps |
| Provider abstraction | RecipeProvider ABC | keeps |
| Persistence | JSON files on disk | **replace** |
| Auth | Single PIN + stateless tokens | **replace** |
| Services | Global singletons | **replace** |
| Frontend framework | Alpine.js (no build) | **replace** |
| Frontend pages | 3 HTML files (index 744, admin 2389, setup 1076) | **replace** |
| Frontend JS | 3 monolith files (app 1475, admin 2714, setup 897) | **replace** |
| CSS | Global (styles 2115, admin 3043, setup 938) | **replace** |
| Build | None | **replace** |
| Tests (backend) | pytest, 475 passing | keeps |
| Tests (frontend) | None | **add** |

## Target stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend framework | FastAPI + Uvicorn | Works fine. No reason to change. |
| Solver | PuLP/CBC | Works fine. |
| Provider abstraction | RecipeProvider ABC | Works fine. Clean boundary. |
| Persistence | SQLite (stdlib sqlite3, WAL mode) | Handles concurrency. Supports queries. Per-user partitioning. Same precedent as roustabout. |
| Auth | Per-user sessions (JWT or session tokens with user identity) | Required for multi-tenant. |
| Services | Per-user service instances or user-scoped queries | Generation lock per user, not global. |
| Frontend framework | Vue 3 (Composition API) + Vite | Component system, TypeScript, router, state management. Aligns with Chris's tooling and Tandoor ecosystem. |
| State management | Pinia | Vue's official state management. Replaces monolithic Alpine data objects. |
| Routing | Vue Router | Client-side routing. Deep linking. Back button. |
| CSS | Scoped component styles + CSS custom properties (keep theme system) | Component isolation. Theme tokens preserved. |
| Build | Vite + TypeScript | Tree-shaking, HMR, content hashing, minification. |
| Tests (frontend) | Vitest + Vue Test Utils | Component unit tests. |
| ORM | None | Hand-rolled queries, thin repository layer. Revisit at decision point DP-3. |

## Migration sequence

The migration has two parallel tracks: backend (persistence + auth + services) and frontend (Vue rewrite). They can proceed somewhat independently since the API contract is the integration boundary.

### Phase M1: Backend — SQLite persistence layer

Replace JSON file I/O with SQLite. No API changes — the REST contract stays identical. Frontend doesn't know the difference.

**Schema (initial):**

```sql
-- Core tables
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE settings (
    user_id INTEGER NOT NULL REFERENCES users(id),
    key TEXT NOT NULL,
    value TEXT NOT NULL,  -- JSON-encoded
    PRIMARY KEY (user_id, key)
);

CREATE TABLE profiles (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    config TEXT NOT NULL,  -- JSON blob (profile definition)
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, name)
);

CREATE TABLE menus (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    profile_name TEXT NOT NULL,
    recipes TEXT NOT NULL,     -- JSON array
    generated_at TEXT NOT NULL,
    metadata TEXT,             -- JSON (warnings, relaxed_constraints, etc.)
    is_current INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE templates (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    config TEXT NOT NULL,  -- JSON blob (template definition)
    UNIQUE(user_id, name)
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    recipe_id INTEGER NOT NULL,
    recipe_name TEXT NOT NULL,
    customer_name TEXT,
    status TEXT NOT NULL DEFAULT 'received',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE generation_history (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    profile_name TEXT NOT NULL,
    recipe_count INTEGER NOT NULL,
    generated_at TEXT NOT NULL,
    metadata TEXT  -- JSON (constraint info, warnings)
);

-- Migration tracking
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now')),
    description TEXT
);
```

**Repository layer:**

Thin data access classes. One per aggregate root. No ORM magic — explicit SQL.

```python
class ProfileRepository:
    def __init__(self, db: sqlite3.Connection):
        self._db = db

    def get_by_name(self, user_id: int, name: str) -> dict | None: ...
    def list_all(self, user_id: int) -> list[dict]: ...
    def save(self, user_id: int, name: str, config: dict) -> None: ...
    def delete(self, user_id: int, name: str) -> None: ...
```

Similar repositories for `MenuRepository`, `SettingsRepository`, `TemplateRepository`, `OrderRepository`, `HistoryRepository`.

**Migration from JSON:**

First-run migration script reads existing `data/` files and inserts into SQLite as user_id=1 (the original single-tenant user). Backward-compatible: if `data/settings.json` exists and database doesn't, auto-migrate.

**Service changes:**

Services receive a `user_id` parameter (from auth middleware) and a database connection (from dependency injection). Replace file I/O calls with repository calls. The service logic (constraint resolution, solver invocation, shopping list aggregation) stays unchanged.

**Concurrency fix:**

Replace the global `asyncio.Lock` on GenerationService with per-user locks:

```python
_user_locks: dict[int, asyncio.Lock] = {}

def _get_lock(user_id: int) -> asyncio.Lock:
    if user_id not in _user_locks:
        _user_locks[user_id] = asyncio.Lock()
    return _user_locks[user_id]
```

User A generating doesn't block User B.

**SSE fix:**

Scope subscriber lists by user_id. Only broadcast to subscribers for the same user.

### Phase M2: Backend — Auth system

Add user registration, login, and session management. The single PIN system becomes one option within a proper auth layer.

- JWT tokens with user_id claim
- Login endpoint (`POST /api/auth/login`)
- Registration endpoint (`POST /api/auth/register`) — may be admin-only or open depending on deployment mode
- Auth middleware extracts user_id from token and injects into request state
- Existing PIN system becomes optional per-user kiosk PIN (separate from login auth)
- Admin role flag on user table for instance-level admin operations

### Phase M3: Frontend — Vue 3 scaffold

Set up the Vue project alongside the existing frontend. Both can coexist during migration (Vue app at `/v2/` or behind a feature flag).

**Project structure:**

```
web-vue/
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── router/
│   │   └── index.ts
│   ├── stores/             # Pinia stores
│   │   ├── auth.ts
│   │   ├── menu.ts
│   │   ├── profiles.ts
│   │   ├── settings.ts
│   │   └── orders.ts
│   ├── composables/        # Shared logic
│   │   ├── useSSE.ts
│   │   ├── useApi.ts
│   │   └── useTheme.ts
│   ├── components/
│   │   ├── menu/
│   │   │   ├── RecipeCard.vue
│   │   │   ├── Carousel.vue
│   │   │   ├── DeckStrip.vue
│   │   │   ├── ShelfTab.vue
│   │   │   └── RecipeDetail.vue
│   │   ├── curation/       # Phase 2
│   │   │   ├── SlotGroup.vue
│   │   │   ├── CandidateCard.vue
│   │   │   └── TimeTally.vue
│   │   ├── shopping/
│   │   │   └── ShoppingList.vue
│   │   ├── admin/
│   │   │   ├── ProfileEditor.vue
│   │   │   ├── ConstraintBuilder.vue
│   │   │   ├── TemplateBuilder.vue
│   │   │   ├── ScheduleEditor.vue
│   │   │   └── SettingsPanel.vue
│   │   ├── auth/
│   │   │   ├── LoginForm.vue
│   │   │   └── RegisterForm.vue
│   │   └── shared/
│   │       ├── BottomSheet.vue
│   │       ├── Modal.vue
│   │       ├── Toast.vue
│   │       ├── IconPicker.vue
│   │       └── ThemeSwitcher.vue
│   ├── views/
│   │   ├── MenuView.vue
│   │   ├── AdminView.vue
│   │   ├── SetupView.vue
│   │   └── LoginView.vue
│   └── types/
│       ├── recipe.ts
│       ├── profile.ts
│       └── api.ts
├── public/
│   ├── icons/
│   └── manifest.json
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

**Migration approach:**

Port one view at a time. Each view is a self-contained Vue component tree that calls the same API endpoints. The API contract doesn't change — Vue just replaces Alpine as the consumer.

**Order of porting:**

1. **Menu view** (index.html → MenuView.vue) — highest user-facing value. RecipeCard, Carousel, DeckStrip components. This validates the component model and SSE integration.
2. **Setup view** (setup.html → SetupView.vue) — wizard flow, good test of form components.
3. **Admin view** (admin.html → AdminView.vue) — largest, most complex. Profile editor, constraint builder, schedule editor. Port last because it benefits most from components built during 1 and 2.

**What carries over unchanged:**
- Theme CSS custom properties (all 16 theme files) — slot into Vue's global styles
- Google Fonts loading
- PWA manifest and service worker (update asset list)
- Icon SVGs

**What gets rewritten:**
- All HTML templates → Vue SFCs
- All JS state management → Pinia stores
- All CSS → scoped component styles + shared theme tokens
- localStorage usage → Pinia persistence plugin

### Phase M4: Frontend — Phase 2 features

With the Vue scaffold in place, build Phase 2 features as Vue components from the start:

- `TemplateBuilder.vue` — admin panel template creation (Decision #1)
- `SlotGroup.vue` + `CandidateCard.vue` — candidate selection with pre-selection (Decision #2)
- `ShoppingList.vue` — provider integration (Decision #5)
- `TimeTally.vue` — running prep/cook time display (Decision #4)
- Curation state in Pinia store — select/deselect/swap per slot

These are the Phase 2 features from `phase2-menu-curation.md`, built on the new stack from day one.

### Phase M5: Cleanup

- Remove old `web/` Alpine frontend
- Remove JSON file I/O code from services
- Update Dockerfile for Vite build step
- Update CI for frontend build + test

## Dockerfile changes

Current: Python-only multi-stage build. Target: add Node build stage for Vite.

```dockerfile
# Stage 1: Frontend build
FROM node:22-slim AS frontend
WORKDIR /app/web-vue
COPY web-vue/package*.json ./
RUN npm ci
COPY web-vue/ ./
RUN npm run build

# Stage 2: Python venv (unchanged)
FROM python:3.14-slim AS builder
# ... existing venv setup ...

# Stage 3: Runtime
FROM python:3.14-slim
# ... existing runtime setup ...
COPY --from=frontend /app/web-vue/dist /app/web/
# Vue build output replaces old web/ static files
```

FastAPI serves the Vue build output as static files, same as today. Vite's build produces `index.html` + hashed assets in `dist/`. Vue Router handles client-side routing; FastAPI catches all non-API routes and serves `index.html` (SPA fallback).

## Database location

SQLite file at `data/morsl.db`. Same volume mount as current `data/` directory. Backup = copy the file (or use `.backup` command). WAL mode for concurrent reads during writes.

## Future decision points

These are decisions we are explicitly deferring. Each has a trigger condition — when the trigger fires, revisit the decision.

### DP-1: PostgreSQL

**Current decision:** SQLite.

**Trigger:** Any of:
- Multiple morsl instances need to share state (horizontal scaling)
- Write contention becomes measurable (SQLite WAL handles moderate concurrency but not heavy write loads)
- We need full-text search beyond SQLite's FTS5

**What changes:** Add PostgreSQL as a Docker Compose service. Replace sqlite3 calls with asyncpg or psycopg3. Repository layer abstracts this — service code shouldn't change.

### DP-2: ORM (SQLAlchemy / Tortoise)

**Current decision:** No ORM. Hand-rolled queries with thin repository layer.

**Trigger:** Any of:
- Table count exceeds 15 and relationship queries become painful
- Multiple developers are writing SQL and consistency is suffering
- We need complex migrations that hand-rolled scripts can't handle cleanly

**What changes:** Introduce SQLAlchemy Core (not ORM) for query building, or full ORM if relationship loading justifies it. Repository layer absorbs the change.

### DP-3: Component library (Vuetify / PrimeVue / Headless UI)

**Current decision:** Custom components with scoped styles. No component library.

**Trigger:** Any of:
- Admin UI complexity exceeds what custom components handle efficiently (data tables, complex forms, date pickers)
- Design consistency is suffering across 20+ components
- Accessibility audit reveals gaps that a library would close for free

**What changes:** Add the library as a dependency. Migrate components incrementally — the library doesn't need to replace everything at once.

### DP-4: SSR / Nuxt

**Current decision:** Client-side SPA served as static files from FastAPI.

**Trigger:** Any of:
- SEO matters (public-facing recipe pages that need to be indexed)
- Initial load performance becomes a problem (large bundle, slow hydration)
- We need server-side auth gates before the JS bundle loads

**What changes:** Move from Vue + Vite to Nuxt. Significant restructuring — pages, layouts, server routes. Worth it only if the triggers are real.

### DP-5: Multi-instance / horizontal scaling

**Current decision:** Single container, single process.

**Trigger:** Any of:
- Multiple users need concurrent generation with different Tandoor instances
- Single-process Uvicorn can't handle the connection count
- We need geographic distribution

**What changes:** Add Redis for shared state (SSE pub/sub, generation queue). Move from SQLite to PostgreSQL (DP-1). Run multiple Uvicorn workers behind a load balancer. Solver jobs move to a task queue (Celery or arq).

### DP-6: Separate frontend deployment

**Current decision:** Vite builds to static files, served by FastAPI.

**Trigger:** Any of:
- Frontend and backend release cycles diverge (frontend shipping daily, backend weekly)
- CDN for static assets becomes valuable (global users, large bundles)
- Frontend team (if one exists) needs independent deploys

**What changes:** Deploy Vue app to CDN or separate static host. FastAPI becomes API-only. CORS configuration needed. Docker image splits into two.

## Risks

1. **Vue rewrite takes longer than expected.** Mitigation: port one view at a time. Old Alpine frontend stays functional until Vue view is ready. Both can coexist.

2. **SQLite migration loses data.** Mitigation: migration script is idempotent and non-destructive. JSON files are not deleted — they become the backup. Migration can be re-run.

3. **Feature freeze during migration.** Mitigation: M1 (SQLite) and M3 (Vue scaffold) can be done in parallel. Bug fixes to the old frontend are still possible. The API doesn't change during M1-M3.

4. **Two frontends to maintain during transition.** Mitigation: keep the transition period short. Port menu view first (highest value), then setup, then admin. Don't maintain both long-term.
