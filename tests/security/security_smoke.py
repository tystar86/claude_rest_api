#!/usr/bin/env python3
"""
Defensive security smoke checks for local/staging use.
Non-destructive, no exploit tooling.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass

import requests


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: str


def check_security_headers(base_url: str) -> CheckResult:
    r = requests.get(f"{base_url}/api/dashboard/", timeout=10)
    xfo = r.headers.get("X-Frame-Options", "")
    xcto = r.headers.get("X-Content-Type-Options", "")
    ok = (
        r.status_code == 200
        and xfo.upper() in {"DENY", "SAMEORIGIN"}
        and xcto.lower() == "nosniff"
    )
    return CheckResult(
        "security_headers", ok, f"status={r.status_code}, xfo={xfo}, xcto={xcto}"
    )


def check_cors_rejects_unknown_origin(base_url: str) -> CheckResult:
    headers = {"Origin": "https://evil.example"}
    r = requests.get(f"{base_url}/api/dashboard/", headers=headers, timeout=10)
    allow_origin = r.headers.get("Access-Control-Allow-Origin")
    ok = allow_origin in (None, "")
    return CheckResult("cors_unknown_origin", ok, f"allow_origin={allow_origin}")


def check_csrf_cookie_issued(base_url: str) -> CheckResult:
    # GET /api/auth/csrf/ must set the csrftoken cookie and return the token in JSON.
    # CSRF is enforced via Django middleware and Ninja's csrf_protect; it only fires when a
    # session exists. Full CSRF-bypass testing therefore requires an authenticated session
    # and is outside the scope of this unauthenticated smoke suite.
    r = requests.get(f"{base_url}/api/auth/csrf/", timeout=10)
    csrf_cookie = r.cookies.get("csrftoken", "")
    json_token = ""
    try:
        json_token = r.json().get("csrfToken", "")
    except Exception:
        pass
    ok = r.status_code == 200 and bool(csrf_cookie or json_token)
    return CheckResult(
        "csrf_cookie_issued",
        ok,
        f"status={r.status_code}, cookie_set={bool(csrf_cookie)}, json_token_set={bool(json_token)}",
    )


def check_sql_injection_probe(base_url: str) -> CheckResult:
    # Probe the post-detail slug endpoint with SQL syntax in the path.
    # The view uses Django ORM (parameterized queries), so the response must be 404,
    # not a crash or a database error. The previous probe targeted a non-existent URL
    # pattern and always returned 404 for the wrong reason.
    probe = "/api/posts/1%27+OR+1%3D1--/"
    r = requests.get(f"{base_url}{probe}", timeout=10)
    body = r.text[:400].lower()
    bad_markers = ("traceback", "sql syntax", "database error", "programmingerror")
    ok = r.status_code in (400, 404) and not any(m in body for m in bad_markers)
    return CheckResult("sql_injection_probe", ok, f"status={r.status_code}")


def check_nosql_style_payload_probe(base_url: str) -> CheckResult:
    # Django isn't NoSQL-backed, but this ensures weird JSON structures fail safely.
    payload = {"email": {"$ne": ""}, "password": {"$ne": ""}}
    r = requests.post(f"{base_url}/api/auth/login/", json=payload, timeout=10)
    body = r.text[:400].lower()
    bad_markers = ("traceback", "typeerror", "attributeerror")
    ok = r.status_code in (400, 403) and not any(m in body for m in bad_markers)
    return CheckResult("nosql_style_payload_probe", ok, f"status={r.status_code}")


def check_xss_payload_not_reflected(base_url: str) -> CheckResult:
    # POST to register with an XSS payload in the username.
    # The API must respond with application/json (never text/html), so the payload
    # cannot be interpreted as markup by the client.  Testing register (rather than
    # login) ensures we hit a code path that actually echoes back user-supplied data
    # on success (username in CurrentUserSerializer).
    payload = '<script>alert("xss")</script>'
    r = requests.post(
        f"{base_url}/api/auth/register/",
        json={
            "email": "xss-probe@example.com",
            "username": payload,
            "password": "testpass1",
        },
        timeout=10,
    )
    content_type = r.headers.get("Content-Type", "")
    is_json = "application/json" in content_type
    reflected_as_html = not is_json and payload in r.text
    ok = is_json and not reflected_as_html
    return CheckResult(
        "xss_reflection_probe",
        ok,
        f"status={r.status_code}, content_type={content_type}",
    )


def check_oversized_payload_rejected(base_url: str) -> CheckResult:
    """POST a 1 MB JSON body to the login endpoint — must not crash (500)."""
    big_value = "A" * (1024 * 1024)  # 1 MB string
    try:
        r = requests.post(
            f"{base_url}/api/auth/login/",
            json={"email": big_value, "password": "x"},
            timeout=15,
        )
        ok = r.status_code in (400, 413, 429)
    except requests.RequestException:
        ok = False
        r = None
    return CheckResult(
        "oversized_payload_rejected",
        ok,
        f"status={r.status_code if r else 'timeout/error'}",
    )


def check_pagination_bounds(base_url: str) -> CheckResult:
    """Verify extreme pagination values return safe responses (not 500)."""
    probes = [
        ("page=-1", "/api/posts/"),
        ("page=999999999", "/api/posts/"),
        ("page=abc", "/api/posts/"),
        ("page=0", "/api/users/"),
    ]
    statuses = []
    for param, path in probes:
        try:
            r = requests.get(f"{base_url}{path}?{param}", timeout=10)
            statuses.append(r.status_code)
        except requests.RequestException:
            statuses.append(-1)
    ok = all(s not in (500, 502, 503) for s in statuses)
    return CheckResult(
        "pagination_bounds",
        ok,
        f"statuses={statuses}",
    )


def check_auth_endpoints_reject_unauthenticated(base_url: str) -> CheckResult:
    """Unauthenticated requests to protected endpoints must return 401/403."""
    protected = [
        ("POST", "/api/auth/logout/"),
        ("PATCH", "/api/auth/profile/"),
    ]
    statuses = []
    for method, path in protected:
        try:
            fn = requests.post if method == "POST" else requests.patch
            r = fn(f"{base_url}{path}", json={}, timeout=10)
            statuses.append(r.status_code)
        except requests.RequestException:
            statuses.append(-1)
    ok = all(s in (401, 403) for s in statuses)
    return CheckResult(
        "auth_endpoints_reject_unauthenticated",
        ok,
        f"statuses={statuses}",
    )


def check_content_type_enforcement(base_url: str) -> CheckResult:
    """API responses must use application/json content type."""
    endpoints = [
        "/api/posts/",
        "/api/dashboard/",
        "/api/tags/",
    ]
    non_json = []
    for path in endpoints:
        try:
            r = requests.get(f"{base_url}{path}", timeout=10)
            ct = r.headers.get("Content-Type", "")
            if "application/json" not in ct:
                non_json.append(f"{path}→{ct}")
        except requests.RequestException:
            non_json.append(f"{path}→error")
    ok = len(non_json) == 0
    return CheckResult(
        "content_type_enforcement",
        ok,
        f"non_json={non_json if non_json else 'none'}",
    )


def run(base_url: str) -> int:
    checks = [
        check_security_headers(base_url),
        check_cors_rejects_unknown_origin(base_url),
        check_csrf_cookie_issued(base_url),
        check_sql_injection_probe(base_url),
        check_nosql_style_payload_probe(base_url),
        check_xss_payload_not_reflected(base_url),
        check_oversized_payload_rejected(base_url),
        check_pagination_bounds(base_url),
        check_auth_endpoints_reject_unauthenticated(base_url),
        check_content_type_enforcement(base_url),
    ]

    print(json.dumps([c.__dict__ for c in checks], indent=2))
    failed = [c for c in checks if not c.ok]
    if failed:
        print(f"FAILED {len(failed)} checks.")
        return 1
    print("All security smoke checks passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()
    return run(args.base_url.rstrip("/"))


if __name__ == "__main__":
    sys.exit(main())
