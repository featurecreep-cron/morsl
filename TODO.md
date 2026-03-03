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

## Phase 3: Ship-Ready Container — COMPLETE (Mar 3, 2026)

- [x] **Release workflow** — tag push → CI → multi-arch build (amd64 + arm64) → GHCR push → Trivy scan → GitHub Release
- [x] **Container scanning (Trivy)** — in release workflow, uploads SARIF to GitHub Security tab
- [x] **User-facing `docker-compose.yml`** — references `ghcr.io/featurecreep-dev/morsl:latest`. Dev version at `docker-compose.dev.yml`
- [x] **Tag v0.1.0** — GitHub release with auto-generated notes: https://github.com/FeatureCreep-dev/morsl/releases/tag/v0.1.0
- [x] **CHANGELOG.md** — v0.1.0 initial release
- [x] **CodeQL workflow** — Python SAST, runs on push/PR and weekly schedule
- [x] **Community infra** — issue templates, PR template, CONTRIBUTING.md
- [x] **Repo topics** — set on GitHub

---

## Phase 4: Quality & Community

- [ ] **GHCR package visibility** — Chris: make package public at github.com/orgs/FeatureCreep-dev/packages
- [ ] **Codecov setup** — Chris: create account, add `CODECOV_TOKEN` repo secret
- [ ] **GitHub Sponsors** — Chris: enable at github.com/sponsors (bank/Stripe setup)
- [ ] **OpenSSF Best Practices** — self-assessment at bestpractices.coreinfrastructure.org (needs GitHub OAuth)
- [x] **Fix B904 (raise from)** — 37 instances, all fixed with `from None`
- [ ] **Fix C901 (complexity)** — 8 functions over threshold, deferred from Phase 2

---

## Phase 5: Documentation & Polish

- [x] **OpenAPI docs** — FastAPI default `/docs` and `/redoc` endpoints, mentioned in README
- [x] **`.editorconfig`** — consistent formatting for contributors
- [ ] **CODE_OF_CONDUCT.md** — standard boilerplate (add when external contributors exist)

---

## Later (post-1.0)

- [ ] **Recipe manager abstraction** — `RecipeSource` protocol for Mealie, Grocy, etc.
- [ ] **Devcontainer** — contributor onboarding
- [ ] **Stale issue bot** — when external contributors exist
