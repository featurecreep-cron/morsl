# Morsl — Implementation TODO

Target: a workable Docker container that a first user can pull, configure, and run.

---

## Phase 1: Code Fixes (from code review) — COMPLETE (Mar 2, 2026)

All findings from the adversarial review addressed. 192 tests passing, 2 skipped (integration).

### Serious (all fixed)

- [x] **proxy.py: Use `DEFAULT_TIMEOUT` from constants.py** — replaced 4 hardcoded `(5, 30)` with imported constant.
- [x] **category_service.py: Use `atomic_write_json()`** — `_save()` now uses atomic writes.
- [x] **icon_mapping_service.py: Use `atomic_write_json()`** — same fix.
- [x] **tandoor_api.py: Fix copy-paste docstrings** — `get_food` and `get_book` now have accurate one-liners.

### Minor (all fixed)

- [x] **models.py:63** — Removed stale comment artifact.
- [x] **models.py:111-126** — Cut `addDetails` docstring to 1 line.
- [x] **models.py:66-93** — Rewrote docstrings to concise one-liners.
- [x] **solver.py:11-14** — Removed redundant class-level attributes.
- [x] **models.py:12** — Renamed `SetEnabledObjects` → `TandoorEntity`.
- [x] **models.py:32,43,49,139,144** — Standardized init parameter to `data` across all model classes.
- [x] **orders.py:32** — Removed dead `hasattr` check.
- [x] **config_service.py:122-126** — Read `base.json` once before loop.
- [x] **proxy.py:174** — Added exception to cook log warning message.
- [x] **Multiple files** — Replaced `filename[:-5]` with `Path(filename).stem` in config_service, template_service.
- [x] **Multiple files** — Added `DEFAULT_CHOICES = 5` to constants.py, replaced 4 hardcoded occurrences.
- [x] **tandoor_api.py:114** — Fixed typo "Deleteing" → "Deleting".
- [ ] **README.md:5** — Test count badge stale. Deferred to Phase 3 (live CI badge).

---

## Phase 2: Ship-Ready Container

The minimum for `docker pull ghcr.io/FeatureCreep-dev/morsl:latest` to work.

- [ ] **Create `.dockerignore`** — exclude tests/, .git/, __pycache__/, *.md (except LICENSE), .github/, .env, .claude/, .cron/, dev scripts
- [ ] **Add OCI labels to Dockerfile** — `org.opencontainers.image.source`, `.version`, `.description`, `.licenses`
- [ ] **Create user-facing `docker-compose.yml`** — references published image (`ghcr.io/...`), not `build: .`. Rename current to `docker-compose.dev.yml`.
- [ ] **Create release workflow** — `.github/workflows/release.yml`: trigger on tag push → build Docker image → push to GHCR
- [ ] **Multi-arch builds** — amd64 + arm64 in release workflow (Raspberry Pi / ARM homelab users)
- [ ] **Tag v0.1.0** — first GitHub release with release notes
- [ ] **SECURITY.md** — standard file pointing to GitHub Security Advisories for reporting vulnerabilities

---

## Phase 3: CI Hardening

Confidence signals that show up as badges and PR checks.

- [ ] **Live CI status badge in README** — replace static "192 passing" with `![CI](...badge.svg)`
- [ ] **Add coverage to CI** — `pytest --cov` + upload to Codecov + coverage badge
- [ ] **Add `ruff format --check .` to CI** — formatting enforcement (one line)
- [ ] **Add mypy to CI** — already in dev deps with `strict = true`, just needs a CI step. May need baseline for existing errors.
- [ ] **Add CodeQL workflow** — `.github/workflows/codeql.yml`. Free SAST for public repos.
- [ ] **Add OpenSSF Scorecard workflow** — `.github/workflows/scorecard.yml` + badge. The gold standard for OSS trust.
- [ ] **CI concurrency control** — `concurrency: { group: ..., cancel-in-progress: true }`
- [ ] **CI dependency caching** — `pip cache` to speed up runs
- [ ] **Docker build test in CI** — verify `docker build .` succeeds on PRs

---

## Phase 4: Dependency & Release Management

- [ ] **Configure Dependabot** — `.github/dependabot.yml` for pip + GitHub Actions ecosystems. Grouped updates.
- [ ] **CHANGELOG.md** — start manually with v0.1.0. Automate with release-drafter or git-cliff later.
- [ ] **Conventional commit enforcement** — commitlint or similar in CI (low priority, enables changelog automation)

---

## Phase 5: Community Infrastructure

- [ ] **Repo topics** — `gh repo edit --add-topic tandoor,meal-planner,menu-generator,docker,selfhosted,fastapi,python,linear-programming`
- [ ] **Issue templates** — `.github/ISSUE_TEMPLATE/bug_report.yml` (YAML form: version, environment, steps to reproduce, expected vs actual)
- [ ] **PR template** — `.github/pull_request_template.md` (checklist: tests pass, description, breaking changes)
- [ ] **CONTRIBUTING.md** — dev setup, testing, PR process, code style
- [ ] **`.pre-commit-config.yaml`** — ruff check, ruff format, trailing-whitespace, detect-private-key, check-yaml
- [ ] **Container scanning (Trivy)** — in release workflow, uploads findings to GitHub Security tab

---

## Phase 6: Documentation & Polish

- [ ] **OpenAPI docs** — verify `/docs` and `/redoc` are accessible, mention in README
- [ ] **`.editorconfig`** — consistent formatting for contributors
- [ ] **CODE_OF_CONDUCT.md** — standard boilerplate
- [ ] **Docs site (MkDocs Material)** — when user-facing docs exceed ~3 pages. Not yet.
- [ ] **CII Best Practices badge** — self-assessment at bestpractices.coreinfrastructure.org. After Phases 1-5 are done.

---

## Later (post-1.0)

- [ ] **Recipe manager abstraction** — `RecipeSource` protocol to support Mealie, Grocy, etc. Real refactor (~2-3 days). Ship Tandoor-only first, abstract if demand exists.
- [ ] **Devcontainer** — for contributor onboarding
- [ ] **Stale issue bot** — when external contributors exist
- [ ] **Auto-labeler on PRs** — when PR volume justifies it
