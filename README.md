# Morsl

**Generate weekly menus from your Tandoor Recipes collection.**

Morsl pulls recipes from your [Tandoor](https://github.com/TandoorRecipes/recipes) instance, applies your constraints (keywords, ratings, ingredients, cook history), and picks a set that satisfies them all. Serve the menu to your household, take orders, and sync selections back to Tandoor as meal plans.

[![CI](https://github.com/FeatureCreep-dev/morsl/actions/workflows/ci.yml/badge.svg)](https://github.com/FeatureCreep-dev/morsl/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/FeatureCreep-dev/morsl/graph/badge.svg)](https://codecov.io/gh/FeatureCreep-dev/morsl)
[![License: MIT](https://img.shields.io/github/license/FeatureCreep-dev/morsl)](LICENSE)
[![GHCR](https://img.shields.io/badge/ghcr.io-morsl-blue?logo=docker)](https://github.com/FeatureCreep-dev/morsl/pkgs/container/morsl)

---

![Customer menu view](docs/screenshot-customer-menu.png)

<details>
<summary>More screenshots</summary>

**Admin panel** — generate menus, manage profiles, configure schedules:

![Admin panel](docs/screenshot-admin.png)

**Setup wizard** — connects to your Tandoor instance in minutes:

![Setup wizard](docs/screenshot-setup.png)

**Mobile** — designed to work on phones (share the menu link with your household):

![Mobile view](docs/screenshot-mobile.png)

</details>

---

## Quick Start

### Docker run (try it out)

```bash
docker run -d --name morsl \
  -e TANDOOR_URL=https://your-tandoor.example.com \
  -e TANDOOR_TOKEN=your-api-token \
  -p 8321:8321 \
  ghcr.io/featurecreep-dev/morsl:latest
```

Open `http://localhost:8321` — you'll see the customer menu view. The admin panel is at `/admin`.

If you skip the environment variables, the setup wizard at `/setup` walks you through connecting to Tandoor.

To find your API token: in Tandoor, go to **Settings > API Tokens**.

### Docker Compose (production)

Create a `docker-compose.yml`:

```yaml
services:
  morsl:
    image: ghcr.io/featurecreep-dev/morsl:latest
    ports:
      - "8321:8321"
    environment:
      - TANDOOR_URL=https://your-tandoor.example.com
      - TANDOOR_TOKEN=your-api-token
      - TZ=America/New_York
    volumes:
      - ./morsl-data:/app/data
    restart: unless-stopped
```

```bash
docker compose up -d
```

The `data` volume persists your profiles, schedules, branding, and settings across container updates.

**Reverse proxy:** Morsl serves on port 8321. Point your reverse proxy at `http://morsl:8321`. No special headers required.

---

## Features

- **Constraint-based generation** — filter by keywords, minimum rating, ingredients, date ranges, recipe books. Constraints can be hard (must satisfy) or soft (best-effort).
- **Multiple profiles** — "Quick Weeknight Dinners," "Breakfast," "Weekend Projects" — each with its own rules.
- **Customer menu view** — shareable page where your household browses the menu, sees recipe photos and ingredients, and places orders.
- **Ordering with notifications** — real-time SSE notifications in the admin panel when someone places an order.
- **Tandoor meal plan sync** — push selected recipes back to Tandoor as meal plan entries.
- **Weekly plans** — template-driven multi-day menus (Monday=quick, Friday=elaborate).
- **Scheduled generation** — cron-based automatic menu refresh.
- **Custom branding** — upload your own logo, favicon, app name, and slogans.
- **Mobile-first customer view** — QR codes for easy sharing, responsive card layout.
- **Setup wizard** — guided 6-step configuration, no config files required.

---

## Configuration

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TANDOOR_URL` | *(none)* | Your Tandoor instance URL |
| `TANDOOR_TOKEN` | *(none)* | Tandoor API token |
| `TZ` | `UTC` | Timezone for schedules and meal plans |
| `LOG_LEVEL` | `INFO` | Python log level |
| `LOG_TO_STDOUT` | `1` (Docker) | Send logs to stdout instead of file |

Both `TANDOOR_URL` and `TANDOOR_TOKEN` can also be configured through the setup wizard (stored in `data/settings.json`).

### Admin panel

All day-to-day configuration happens through the admin UI at `/admin`:

- **Generate tab** — pick a profile, generate a menu, manage schedules
- **Profiles tab** — create and edit constraint profiles (supports a `base.json` whose constraints apply to all profiles)
- **Weekly tab** — build multi-day menu templates
- **Settings tab** — branding, Tandoor connection, data management

Three complexity tiers (Standard / Advanced / Expert) progressively reveal more controls.

---

## How It Works

1. **Profiles** define constraints: which keywords to include/exclude, minimum ratings, date ranges, food requirements.
2. The **solver** (PuLP/CBC) finds a feasible recipe set satisfying all hard constraints while minimizing soft constraint violations.
3. If no solution exists at the requested count, it reduces progressively down to `min_choices`.
4. Generated menus are served to the **customer view** for browsing and ordering.
5. Orders sync back to Tandoor as **meal plan** entries.

---

## Development

Requires Python 3.12+ and system libraries for CairoSVG (`libcairo2`, `libpango-1.0-0`).

```bash
pip install -e ".[dev]"
pytest
```

216 tests covering the solver, services, API routes, models, and utilities. Integration tests requiring a live Tandoor instance are marked `@pytest.mark.integration` and skipped by default.

### Tech stack

- **Backend**: FastAPI, Pydantic, uvicorn
- **Solver**: PuLP with CBC (COIN-OR)
- **Frontend**: Vanilla JS with Alpine.js, no build step
- **Scheduling**: APScheduler 3.x
- **Container**: Multi-arch Docker (amd64 + arm64), auto-release pipeline

### Project structure

```
morsl/
├── app/                    # FastAPI application
│   ├── main.py             # Lifespan, middleware, page routes
│   ├── config.py           # Pydantic Settings
│   └── api/
│       ├── dependencies.py # DI singletons, auth
│       ├── models.py       # Request/response schemas
│       └── routes/         # API endpoints
├── services/               # Business logic layer
├── web/                    # Frontend (vanilla JS, Alpine.js)
├── solver.py               # PuLP-based recipe picker
├── models.py               # Domain models
├── tandoor_api.py          # Tandoor API client
├── Dockerfile
└── docker-compose.yml
```

---

## Support

- [File an issue](https://github.com/FeatureCreep-dev/morsl/issues) on GitHub
- Built by [Feature Creep](https://featurecreep.dev) — an AI builds things in public, a human keeps it honest

## License

[MIT](LICENSE)
