# Security Checklist (Frontend + Backend)

Use this list before release and after major auth/API changes.

## Backend Checks

- Authentication required for state-changing operations (`POST`, `PATCH`, `DELETE`).
- CSRF enforced for session-authenticated write endpoints.
- Authorization checks in place (owner/mod/admin) for edit/delete operations.
- Rate limiting active:
  - per anonymous IP (`anon`)
  - per authenticated user (`user`)
  - per endpoint + actor (`endpoint_actor`)
  - global overall cap (`api_global`)
- API never returns stack traces in production (`DEBUG=False`).
- CORS restricted to known frontend origins only.
- Security headers present (`X-Frame-Options`, `X-Content-Type-Options`).
- Input validation for body fields, IDs, and enum values.
- SQL injection attempts return safe errors/404 (no DB errors leaked).
- Unexpected JSON structures (NoSQL-style payloads) fail safely (4xx, not 5xx).

## Frontend Checks

- Authentication state handled securely (no sensitive data in localStorage).
- Forms escape/render user content safely (no dangerous HTML insertion).
- API errors do not expose backend internals.
- CSRF cookie/token flow works for authenticated writes.
- Route guards/navigation enforce intended access behavior.
- Unsafe links/scripts are not injected from user content.

## Recommended Runbook

1. Run security smoke probes:

```bash
python3 tests/security/security_smoke.py --base-url http://localhost:8000
```

2. Run controlled burst/load probe (safe local test):

```bash
python3 tests/security/load_burst.py --url http://localhost:8000/api/dashboard/ --requests 200 --concurrency 20
```

3. Verify some requests return `429` when limits are exceeded.

4. Review logs for unexpected `500` responses.
