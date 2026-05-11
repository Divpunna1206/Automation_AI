from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = os.environ.get("JOB_ASSISTANT_API_BASE", "http://localhost:8000").rstrip("/")
ENDPOINTS = [
    "/health",
    "/system/health-check",
    "/jobs/queue",
    "/dashboard/daily-target",
    "/analytics/overview",
    "/outreach/dashboard",
]


def get_json(path: str) -> dict:
    request = Request(f"{BASE_URL}{path}", headers={"Accept": "application/json"})
    with urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    print(f"Smoke testing {BASE_URL}")
    failures = 0
    for endpoint in ENDPOINTS:
        try:
            payload = get_json(endpoint)
            print(f"OK {endpoint}: {summarize(payload)}")
        except HTTPError as exc:
            failures += 1
            print(f"FAIL {endpoint}: HTTP {exc.code}")
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            failures += 1
            print(f"FAIL {endpoint}: {exc}")
    if failures:
        print(f"{failures} smoke checks failed.")
        return 1
    print("All smoke checks passed.")
    return 0


def summarize(payload: dict) -> str:
    keys = list(payload.keys())[:6]
    return ", ".join(keys) if keys else "empty object"


if __name__ == "__main__":
    sys.exit(main())
