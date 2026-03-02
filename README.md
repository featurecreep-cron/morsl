# Morsl

[![CI](https://github.com/FeatureCreep-dev/morsl/actions/workflows/ci.yml/badge.svg)](https://github.com/FeatureCreep-dev/morsl/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/FeatureCreep-dev/morsl/graph/badge.svg)](https://codecov.io/gh/FeatureCreep-dev/morsl)
[![License: MIT](https://img.shields.io/github/license/FeatureCreep-dev/morsl)](LICENSE)
[![Python](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FFeatureCreep-dev%2Fmorsl%2Fmain%2Fpyproject.toml)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A menu generator for [Tandoor Recipes](https://github.com/TandoorRecipes/recipes). Define constraints (keywords, ratings, foods, dates) and Morsl uses linear programming to pick recipes that satisfy them all.

Comes with a customer-facing menu view, an admin panel for configuration, and optional sync back to Tandoor as meal plans.

## Quickstart (Docker)

```bash
cp .env.example .env
# Edit .env with your Tandoor URL and API token

docker compose up -d
```

Open `http://localhost:8321` for the menu, `http://localhost:8321/admin` for configuration.

If you skip the `.env` file, the setup wizard at `/setup` will walk you through connecting to Tandoor.

## Quickstart (bare metal)

Requires Python 3.12+ and system libraries for CairoSVG (`libcairo2`, `libpango-1.0-0`).

```bash
pip install .
cp .env.example .env
# Edit .env

uvicorn app.main:app --host 0.0.0.0 --port 8321
```

Or use the included helper script:

```bash
./morsl.sh start     # start in background
./morsl.sh stop      # stop
./morsl.sh restart   # restart
./morsl.sh status    # check if running
```

## How it works

1. **Profiles** define how menus are generated. Each profile specifies a number of recipes to pick and a set of constraints.
2. **Constraints** filter and score recipes. Types include keyword inclusion/exclusion, minimum ratings, date ranges (created, last cooked), food requirements, and recipe book membership.
3. The **solver** (PuLP/CBC) finds a feasible set of recipes that satisfies all hard constraints while minimizing soft constraint violations. If no solution exists at the requested count, it reduces progressively down to `min_choices`.
4. Generated menus are served to the **customer view**, where users can browse recipes and place orders.
5. Orders can optionally sync back to Tandoor as **meal plan** entries.

## Configuration

All configuration happens through the admin UI at `/admin`. Key concepts:

- **Profiles**: Named configurations with constraints. Supports a `base.json` profile whose constraints are inherited by all others.
- **Constraints**: `>=`, `<=`, `==`, `between` operators. Each can be hard (must satisfy) or soft (penalty-weighted).
- **Scheduling**: Cron-based automatic generation via APScheduler.
- **Weekly plans**: Template-driven multi-day menu generation.
- **Orders**: Customer ordering with real-time SSE notifications to the admin panel.
- **Branding**: Custom logo, favicon, loading icon, app name, and slogans.

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TANDOOR_URL` | *(none)* | Tandoor instance URL |
| `TANDOOR_TOKEN` | *(none)* | Tandoor API token |
| `LOG_LEVEL` | `INFO` | Python log level |
| `LOG_TO_STDOUT` | `0` | Send logs to stdout instead of file (enabled by default in Docker) |

Credentials can also be configured through the setup wizard (stored as base64 in `data/settings.json`).

## Project structure

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
├── models.py               # Domain models (Recipe, Food, Keyword, etc.)
├── tandoor_api.py          # Tandoor API client with caching and retry
├── utils.py                # Shared utilities
├── constants.py            # Magic numbers and defaults
├── Dockerfile
├── docker-compose.yml
└── morsl.sh                # Dev/prod helper script
```

## Testing

```bash
pip install -e ".[dev]"
pytest
```

214 tests covering the solver, services, API routes, models, and utilities. Integration tests that require a live Tandoor instance are marked `@pytest.mark.integration` and skipped by default.

## Tech stack

- **Backend**: FastAPI, Pydantic, uvicorn
- **Solver**: PuLP with CBC (COIN-OR)
- **Frontend**: Vanilla JS with Alpine.js, no build step
- **Scheduling**: APScheduler 3.x
- **Image processing**: Pillow, CairoSVG, py-svg-hush (SVG sanitization)
- **API client**: requests with connection pooling and retry

## License

[MIT](LICENSE)
