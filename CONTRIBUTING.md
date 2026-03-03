# Contributing to Morsl

## Dev setup

Requires Python 3.12+ and system libraries for CairoSVG.

```bash
# Ubuntu/Debian
sudo apt-get install libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 shared-mime-info

# Install in editable mode with dev deps
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
```

Integration tests (require a live Tandoor instance) are skipped by default. Run them with:

```bash
pytest -m integration
```

## Code style

This project uses [Ruff](https://github.com/astral-sh/ruff) for linting and formatting.

```bash
ruff check .          # lint
ruff format --check . # format check
ruff format .         # auto-format
```

Both checks run in CI. PRs that fail either check will not merge.

## Docker

```bash
docker build .                          # verify build
docker compose -f docker-compose.dev.yml up  # run locally with build context
```

## PR process

1. Fork the repo and create a branch from `main`.
2. Make your changes. Add tests for new behavior.
3. Ensure `pytest`, `ruff check .`, `ruff format --check .`, and `docker build .` all pass.
4. Open a PR against `main`. Fill in the template.
5. CI must pass before merge.
