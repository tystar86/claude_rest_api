#!/usr/bin/env python3
"""
Controlled burst test for rate-limit verification.
Safe local/staging load only (not DDoS tooling).
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

DEFAULT_ENDPOINTS = [
    "/api/dashboard/",
    "/api/posts/",
    "/api/users/",
    "/api/tags/",
    "/api/comments/",
]


def single_request(url: str, timeout: float) -> int:
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code
    except requests.RequestException:
        return -1


def run(url: str, requests_count: int, concurrency: int, timeout: float) -> int:
    statuses: Counter[int] = Counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [
            pool.submit(single_request, url, timeout) for _ in range(requests_count)
        ]
        for f in as_completed(futures):
            statuses[f.result()] += 1

    print("Status counts:", dict(statuses))
    if 429 in statuses:
        print("Rate limiting observed (429 present).")
        return 0
    print(
        "No 429 observed. The default anon throttle is 120/min. "
        "Run with --requests 250 --concurrency 50 to reliably exceed it, "
        "or temporarily lower DRF_THROTTLE_ANON in .env to confirm throttling is active."
    )
    return 1


def run_all_endpoints(
    base_url: str, requests_count: int, concurrency: int, timeout: float
) -> int:
    """Run burst test against all DEFAULT_ENDPOINTS and print a summary table."""
    results: list[tuple[str, Counter[int], bool]] = []
    for path in DEFAULT_ENDPOINTS:
        url = f"{base_url}{path}"
        print(f"\n--- Burst: {url} ---")
        statuses: Counter[int] = Counter()
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [
                pool.submit(single_request, url, timeout) for _ in range(requests_count)
            ]
            for f in as_completed(futures):
                statuses[f.result()] += 1
        throttled = 429 in statuses
        print("Status counts:", dict(statuses))
        print("Rate limiting observed." if throttled else "No 429 observed.")
        results.append((path, statuses, throttled))

    print("\n=== Summary ===")
    print(f"{'Endpoint':<25} {'Throttled':>10} {'Status counts'}")
    print("-" * 60)
    for path, statuses, throttled in results:
        print(f"{path:<25} {'YES' if throttled else 'NO':>10}  {dict(statuses)}")

    not_throttled = [path for path, _, throttled in results if not throttled]
    if not_throttled:
        print(f"\nWARNING: No 429 observed for: {not_throttled}")
        return 1
    print("\nAll endpoints exhibited rate limiting.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Controlled burst test for rate-limit verification."
    )
    parser.add_argument("--url", default="http://localhost:8000/api/dashboard/")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument(
        "--all-endpoints",
        action="store_true",
        help="Test all default API endpoints sequentially.",
    )
    args = parser.parse_args()
    if args.all_endpoints:
        return run_all_endpoints(
            args.base_url.rstrip("/"), args.requests, args.concurrency, args.timeout
        )
    return run(args.url, args.requests, args.concurrency, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
