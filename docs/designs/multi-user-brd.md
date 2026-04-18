# Multi-User Support — Business Requirements

Status: **future** — not scheduled, captured for when the time comes.

## Context

morsl is currently single-operator, single-kiosk. All configuration is global, all recipes are visible to all viewers, and there is one admin PIN. This document captures requirements that must be addressed before morsl can support multiple users or tenants.

## Requirements

### Authentication & Authorization

1. **Recipe proxy auth (MED-3 from security audit 2026-04-05)**: The `/api/recipe/{id}` proxy endpoint currently has no authentication. Any client on the network can fetch full recipe details by ID. In a single-kiosk deployment this is intentional — the kiosk display needs unauthenticated access. In a multi-user deployment, this becomes an IDOR vulnerability: any authenticated user could access any other user's private recipes by guessing IDs. **Must be gated by user/tenant context before multi-user ships.**

2. Per-user credentials: Each user needs their own Tandoor URL + token pair, replacing the current global credential model.

3. Session model: Replace the single admin PIN with per-user authentication (OAuth, password, or similar).

## Dependencies

- Security audit finding MED-3 (`docs/audits/security-audit-2026-04-05.md`)
