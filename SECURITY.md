# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it through
[GitHub Security Advisories](https://github.com/featurecreep-cron/morsl/security/advisories/new).

Do not open a public issue for security vulnerabilities.

## Response Timeline

- **Acknowledgment:** within 48 hours
- **Initial assessment:** within 7 days
- **Fix or mitigation:** depends on severity, but we aim for 30 days for critical issues

## Supported Versions

Only the latest release is supported with security updates.

## Scope

Morsl is a self-hosted application. Security issues include authentication bypass, path traversal, injection vulnerabilities, and token exposure. Issues that require local filesystem access or Docker socket access are generally out of scope (if an attacker has those, you have bigger problems).
