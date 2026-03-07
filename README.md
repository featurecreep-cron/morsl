# Morsl

**Generate weekly menus from your Tandoor Recipes collection.**

Morsl connects to your [Tandoor Recipes](https://github.com/TandoorRecipes/recipes) instance, picks recipes based on your preferences (keywords, ratings, ingredients, cook history), and serves a menu your household can browse and order from. Selections sync back to Tandoor as meal plans.

[![CI](https://github.com/FeatureCreep-dev/morsl/actions/workflows/ci.yml/badge.svg)](https://github.com/FeatureCreep-dev/morsl/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/github/license/FeatureCreep-dev/morsl)](LICENSE)
[![GHCR](https://img.shields.io/badge/ghcr.io-morsl-blue?logo=docker)](https://github.com/FeatureCreep-dev/morsl/pkgs/container/morsl)

---

![Customer menu view — recipe cards with photos, ratings, ingredients, and ordering](docs/screenshot-customer-menu.png)

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

## What You Need

- A running [Tandoor Recipes](https://docs.tandoor.dev) instance
- A Tandoor API token (in Tandoor: **Settings > API Tokens > Create**)
- Docker installed on your server

## Quick Start

### Docker Compose (recommended)

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
      - morsl-data:/app/data
    restart: unless-stopped

volumes:
  morsl-data:
```

```bash
docker compose up -d
```

Open `http://your-server:8321`. The setup wizard walks you through connecting to Tandoor if you skip the environment variables.

The `data` volume keeps your profiles, schedules, branding, and settings safe across updates.

### Docker run (quick test)

```bash
docker run -d --name morsl \
  -e TANDOOR_URL=https://your-tandoor.example.com \
  -e TANDOOR_TOKEN=your-api-token \
  -p 8321:8321 \
  ghcr.io/featurecreep-dev/morsl:latest
```

**Note:** Without a volume mount (`-v`), your settings are lost when the container restarts. Use Docker Compose for anything permanent.

---

## How It Works

1. **Create profiles** in the admin panel (`/admin`). Each profile defines what kind of recipes to pick — "Weeknight Dinner" might require the keyword "entree" and prefer 4+ star recipes. "Breakfast" might pick 3 recipes tagged "breakfast."
2. **Generate a menu.** Morsl picks recipes that match your rules. If your rules are too strict, it picks fewer recipes rather than giving you nothing.
3. **Share the menu.** Your household opens `http://your-server:8321` on their phone or computer — no accounts needed. They browse recipe cards, see photos and ingredients, and tap to order.
4. **Orders appear** instantly in the admin panel. Selections can sync back to Tandoor as meal plan entries.

---

## Features

- **Multiple profiles** — "Weeknight Dinner," "Breakfast," "Weekend Projects" — each with its own rules
- **Smart filtering** — filter by keywords, minimum rating, ingredients, date ranges, recipe books. Rules can be strict (must match) or flexible (prefer but don't require)
- **Household menu** — shareable page where your family browses and orders, no accounts needed
- **Live order notifications** — the admin panel updates instantly when someone places an order
- **Tandoor meal plan sync** — push selections back to Tandoor
- **Weekly plans** — assign different profiles to different days and meal types (breakfast from one profile, dinner from another)
- **Scheduled generation** — automatic menu refresh on a schedule
- **Custom branding** — your own logo, favicon, app name, and slogans
- **Mobile-friendly** — responsive layout, QR codes for easy sharing from desktop
- **Setup wizard** — guided 6-step configuration, no config files required
- **Works with any recipe collection** — even if your recipes aren't tagged or rated, Morsl still picks from them. Tags and ratings just give you more control.

---

## Configuration

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TANDOOR_URL` | *(none)* | Your Tandoor instance URL |
| `TANDOOR_TOKEN` | *(none)* | Tandoor API token |
| `TZ` | `UTC` | Timezone for schedules and meal plans |
| `LOG_LEVEL` | `INFO` | Log verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOG_TO_STDOUT` | `1` (Docker) | Send logs to stdout instead of file |

Both `TANDOOR_URL` and `TANDOOR_TOKEN` can also be configured through the setup wizard.

### Admin panel

Everything is configured through the admin UI at `/admin`:

- **Generate** — pick a profile, generate a menu, set up automatic schedules
- **Profiles** — create and edit profiles with filtering rules
- **Weekly** — build multi-day menu templates (different profiles per day and meal type)
- **Settings** — branding, Tandoor connection, data management

Three complexity tiers (Standard / Advanced / Expert) progressively show more options. Start with Standard — it covers most use cases.

### Security

Morsl has no built-in authentication by default. If you're only using it at home on your local network, this is fine. If you're exposing it to the internet, put it behind a reverse proxy with authentication (Authelia, Authentik, etc.) or enable the admin PIN in Settings.

---

## Development

<details>
<summary>For contributors and developers</summary>

Requires Python 3.12+ and system libraries for CairoSVG (`libcairo2`, `libpango-1.0-0`).

```bash
pip install -e ".[dev]"
pytest
```

216 tests covering the solver, services, API routes, models, and utilities. Integration tests requiring a live Tandoor instance are marked `@pytest.mark.integration` and skipped by default.

### Tech stack

- **Backend**: FastAPI, Pydantic, uvicorn
- **Solver**: PuLP with CBC (COIN-OR) — linear programming for recipe selection
- **Frontend**: Vanilla JS with Alpine.js, no build step
- **Scheduling**: APScheduler 3.x
- **Container**: python:3.12-slim (Debian), multi-arch (amd64 + arm64), auto-release pipeline

The Docker image uses `python:3.12-slim` rather than Alpine because CairoSVG and Pango require system libraries that are simpler to install on Debian.

The image runs as UID 1000 by default. To change this, rebuild with `--build-arg UID=<your-uid> --build-arg GID=<your-gid>`.

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

[![codecov](https://codecov.io/gh/FeatureCreep-dev/morsl/graph/badge.svg)](https://codecov.io/gh/FeatureCreep-dev/morsl)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/FeatureCreep-dev/morsl/badge)](https://scorecard.dev/viewer/?uri=github.com/FeatureCreep-dev/morsl)
[![Python](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FFeatureCreep-dev%2Fmorsl%2Fmain%2Fpyproject.toml)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Sponsor](https://img.shields.io/badge/sponsor-FeatureCreep-ea4aaa?logo=github-sponsors)](https://github.com/sponsors/FeatureCreep-dev)

</details>

---

## Support

- [File an issue](https://github.com/FeatureCreep-dev/morsl/issues) on GitHub
- [Buy me a coffee](https://buymeacoffee.com/featurecreep)
- Built by [Cron](https://featurecreep.dev)

## License

[MIT](LICENSE)
