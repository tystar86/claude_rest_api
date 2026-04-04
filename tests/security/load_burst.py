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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000/api/dashboard/")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args()
    return run(args.url, args.requests, args.concurrency, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
