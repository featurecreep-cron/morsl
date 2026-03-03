# Morsl — Implementation TODO

Target: a workable Docker container that a first user can pull, configure, and run.

---

## Phase 1: Code Fixes — COMPLETE (Mar 2, 2026)

All findings from the adversarial code review addressed. 214 tests passing, 2 skipped (integration).

---

## Phase 2: Repo & CI Foundation — COMPLETE (Mar 2, 2026)

- [x] GitHub repo (`FeatureCreep-dev/morsl`), signed commits, GPG key on GitHub
- [x] `.dockerignore`, OCI labels on Dockerfile
- [x] CI decomposed: `ci.yml` (reusable), `push.yml` (main branch), `dependabot-automerge.yml`
- [x] Lint (ruff check + format), test with coverage, Docker build test
- [x] Concurrency control, pip caching
- [x] Dependabot: pip (daily, grouped by semver), GitHub Actions (weekly), Docker (weekly)
- [x] Dependabot auto-merge: PRs auto-approved + merged after CI passes
- [x] Branch protection: lint/test/docker required status checks
- [x] `SECURITY.md`, OpenSSF Scorecard workflow + badge
- [x] Live README badges: CI, Codecov, OpenSSF Scorecard, License, Python, Ruff, GHCR, Sponsor

---

## Phase 3: Ship-Ready Container

The minimum for `docker pull ghcr.io/featurecreep-dev/morsl:latest` to work.

- [ ] **Release workflow** — `.github/workflows/release.yml`: tag push → build multi-arch image (amd64 + arm64) → push to GHCR
- [ ] **Container scanning (Trivy)** — in release workflow, upload findings to GitHub Security tab
- [ ] **User-facing `docker-compose.yml`** — references published GHCR image. Rename current to `docker-compose.dev.yml`
- [ ] **Tag v0.1.0** — first GitHub release with release notes
- [ ] **CHANGELOG.md** — start with v0.1.0

---

## Phase 4: Quality & Community

- [ ] **Codecov setup** — Chris: create account, add `CODECOV_TOKEN` repo secret
- [ ] **GitHub Sponsors** — Chris: enable at github.com/sponsors (bank/Stripe setup)
- [ ] **OpenSSF Best Practices** — self-assessment at bestpractices.coreinfrastructure.org
- [ ] **CodeQL workflow** — `.github/workflows/codeql.yml`, free SAST for public repos
- [ ] **Repo topics** — tandoor, meal-planner, menu-generator, docker, selfhosted, fastapi, python, linear-programming
- [ ] **Issue templates** — `.github/ISSUE_TEMPLATE/bug_report.yml`
- [ ] **PR template** — `.github/pull_request_template.md`
- [ ] **CONTRIBUTING.md** — dev setup, testing, PR process, code style
- [ ] **Fix B904 (raise from)** — 37 instances, deferred from Phase 2 lint cleanup
- [ ] **Fix C901 (complexity)** — 8 functions over threshold, deferred from Phase 2

---

## Phase 5: Documentation & Polish

- [ ] **OpenAPI docs** — verify `/docs` and `/redoc` accessible, mention in README
- [ ] **`.editorconfig`** — consistent formatting for contributors
- [ ] **CODE_OF_CONDUCT.md** — standard boilerplate

---

## Later (post-1.0)

- [ ] **Recipe manager abstraction** — `RecipeSource` protocol for Mealie, Grocy, etc.
- [ ] **Devcontainer** — contributor onboarding
- [ ] **Stale issue bot** — when external contributors exist
