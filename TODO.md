# Morsl — Implementation TODO

Target: a workable Docker container that a first user can pull, configure, and run.

---

## Phase 1: Code Fixes (from code review) — COMPLETE (Mar 2, 2026)

All findings from the adversarial review addressed. 212 tests passing, 2 skipped (integration).
Post-review fixes: restored missing `import json` in category_service.py, added 21 CategoryService tests,
removed dead `_parse_date_filter` method.

---

## Phase 2: Repo & CI Foundation

Get the repo on GitHub with live CI, real badges, and a clean build.

- [ ] **Create GitHub repo** — `FeatureCreep-dev/morsl`, push initial commit
- [ ] **Create `.dockerignore`** — exclude tests/, .git/, __pycache__/, *.md (except LICENSE), .github/, .env, .claude/, dev scripts
- [ ] **Add OCI labels to Dockerfile** — `org.opencontainers.image.source`, `.version`, `.description`, `.licenses`
- [ ] **Live README badges** — replace all static badges with dynamic ones:
  - CI status (GitHub Actions workflow badge)
  - Coverage % (pytest-cov → Codecov)
  - License (shields.io from GitHub API)
  - Python version (shields.io from pyproject.toml)
  - Code style: ruff (static convention badge)
- [ ] **Add coverage to CI** — `pytest --cov` + upload to Codecov + coverage badge
- [ ] **Add `ruff format --check .` to CI** — formatting enforcement
- [ ] **CI concurrency control** — `concurrency: { group: ..., cancel-in-progress: true }`
- [ ] **CI dependency caching** — `pip cache` to speed up runs
- [ ] **Docker build test in CI** — verify `docker build .` succeeds on PRs
- [ ] **Configure Dependabot** — `.github/dependabot.yml` for pip + GitHub Actions ecosystems. Grouped updates.
- [ ] **SECURITY.md** — standard file pointing to GitHub Security Advisories

---

## Phase 3: Ship-Ready Container

The minimum for `docker pull ghcr.io/FeatureCreep-dev/morsl:latest` to work.

- [ ] **Create user-facing `docker-compose.yml`** — references published image (`ghcr.io/...`), not `build: .`. Rename current to `docker-compose.dev.yml`.
- [ ] **Create release workflow** — `.github/workflows/release.yml`: trigger on tag push → build Docker image → push to GHCR
- [ ] **Multi-arch builds** — amd64 + arm64 in release workflow (Raspberry Pi / ARM homelab users)
- [ ] **Container scanning (Trivy)** — in release workflow, uploads findings to GitHub Security tab
- [ ] **Tag v0.1.0** — first GitHub release with release notes
- [ ] **CHANGELOG.md** — start manually with v0.1.0

---

## Phase 4: CI Hardening & Community

Additional confidence signals and contributor infrastructure.

- [ ] **Add mypy to CI** — already in dev deps with `strict = true`, just needs a CI step. May need baseline for existing errors.
- [ ] **Add CodeQL workflow** — `.github/workflows/codeql.yml`. Free SAST for public repos.
- [ ] **Add OpenSSF Scorecard workflow** — `.github/workflows/scorecard.yml` + badge.
- [ ] **Repo topics** — `gh repo edit --add-topic tandoor,meal-planner,menu-generator,docker,selfhosted,fastapi,python,linear-programming`
- [ ] **Issue templates** — `.github/ISSUE_TEMPLATE/bug_report.yml`
- [ ] **PR template** — `.github/pull_request_template.md`
- [ ] **CONTRIBUTING.md** — dev setup, testing, PR process, code style
- [ ] **`.pre-commit-config.yaml`** — ruff check, ruff format, trailing-whitespace, detect-private-key, check-yaml

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
