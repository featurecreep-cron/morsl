# Morsl

Automated menu generator for Tandoor Recipes. LP solver with constraint profiles, weekly templates, scheduled generation, and order tracking.

## Before Writing Code

Read the relevant conventions doc before starting work:

**Conventions location:** `~/featurecreep/docs/morsl/development/`

| When you're about to... | Read this |
|------------------------|-----------|
| Create or modify a module | `coding-conventions.md` → Layer Invariant, Naming, Imports |
| Add error handling | `coding-conventions.md` → Error Handling |
| Touch domain models | `coding-conventions.md` → Data Modeling |
| Touch HTTP client code | `coding-conventions.md` → HTTP Client Constraints |
| Write or modify tests | `testing-patterns.md` |

## Architecture Constraints (always in effect)

These are non-negotiable. Violations are caught by `tests/test_architecture.py`.

1. **Layer invariant:** Routes → Services → Core → Foundation. No upward imports.
2. **Sync solver:** `solver.py` and `tandoor_api.py` never import asyncio.
3. **TandoorAPI is sole HTTP client for Tandoor.** Proxy routes are the documented exception.
4. **`import requests` only in `tandoor_api.py` and `routes/proxy.py`.**
5. **TandoorAPI instantiation only in service modules**, never in routes.
6. **Frozen domain models.** `GenerationStatus` and `WeeklyGenerationStatus` are the documented exceptions.
7. **Tokens never in logs.** No f-string with "token" in logger calls.
8. **Service singletons via `dependencies.py` only.** No service instantiates another service directly (workflow composition via method parameters is fine).

## Code Style (enforced by ruff — will fail CI)

- Line length: 99
- Formatter: ruff format (double quotes)
- Linter: ruff (E, W, F, I, C, B, ANN, RUF, S, PT, SIM)
- Type checker: mypy strict
- Catch specific exceptions. `except Exception` needs `# noqa: broad-except` with justification.

## After Writing Code

Run `/code-review morsl/{module}` on every module after completing a phase.

## Branching Strategy

- **`main`** — production and GitHub default branch. Every push auto-releases a new version + Docker image. Branch-protected (PR required).
- **`develop`** — integration branch for development. CI runs on every push.
- **Feature branches** — off `develop` for multi-commit or risky changes.
- **Release flow:** merge `develop` → `main` via PR when ready to ship.

Never push directly to `main`. All work lands on `develop` first.

## Dev Commands

```bash
# Lint + format check
cd ~/morsl-work && conda run -n morsl ruff check . && ruff format --check .

# Tests
conda run -n morsl python -m pytest --tb=short -q

# Tests with coverage
conda run -n morsl python -m pytest --cov=morsl --cov-branch --cov-report=term-missing

# Single test file
conda run -n morsl python -m pytest tests/test_solver.py -v
```

## Key Files

- `pyproject.toml` — dependencies, tool config, Python version
- `morsl/models.py` — domain models (start here to understand the domain)
- `morsl/solver.py` — LP constraint solver
- `morsl/tandoor_api.py` — Tandoor HTTP client (sole consumer of `requests`)
- `morsl/app/api/dependencies.py` — DI registry, service singletons
- `morsl/services/menu_service.py` — core generation logic
- `tests/conftest.py` — shared test fixtures
- `~/featurecreep/docs/morsl/` — architecture, BRD, dev guidelines (private)
