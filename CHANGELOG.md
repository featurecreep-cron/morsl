# Changelog

## v0.1.0 (2026-03-02)

Initial public release.

### Features

- Constraint-based menu generation using linear programming (PuLP/CBC)
- Constraint types: keyword, food, book, rating, cooked date, created date
- Operators: `>=`, `<=`, `==`, `between`, with hard and soft (weighted) modes
- Profile system with base profile inheritance
- Customer-facing menu view with order placement
- Admin panel for profiles, categories, branding, and scheduling
- Cron-based automatic menu generation (APScheduler)
- Weekly plan templates with multi-day generation
- Real-time order notifications via SSE
- Tandoor API integration with caching and retry
- Setup wizard for first-time configuration
- Custom branding (logo, favicon, loading icon, app name, slogans)
- Docker image with non-root user, health check, multi-arch (amd64 + arm64)

### Infrastructure

- CI: lint (ruff check + format), test with coverage, Docker build
- OpenSSF Scorecard, CodeQL SAST
- Dependabot with auto-merge for passing updates
- Trivy container scanning on release
