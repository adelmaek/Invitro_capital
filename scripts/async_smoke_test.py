# DIFF SUMMARY:
# - Updated POST payload to prompt-based request body.
"""Async API smoke test for Celery-backed analysis jobs.

Requires:
1) redis-server
2) uvicorn app.main:app --reload
3) celery -A worker.celery_app.celery worker --loglevel=WARNING
"""

from __future__ import annotations

import sys
import time

import requests

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT_SECONDS = 60


def main() -> None:
    payload = {"prompt": "Analyze the company whose ticker GOOGL. Return only JSON."}
    print("[SMOKE] App sent API request: POST /analysis")
    post_resp = requests.post(f"{BASE_URL}/analysis", json=payload, timeout=10)
    post_resp.raise_for_status()
    job_id = post_resp.json()["job_id"]
    print(f"[SMOKE] Job created: job_id={job_id}")

    deadline = time.time() + TIMEOUT_SECONDS
    poll_count = 0
    print("[SMOKE] Polling job status...")
    while time.time() < deadline:
        poll_count += 1
        status_resp = requests.get(f"{BASE_URL}/analysis/{job_id}", timeout=10)
        status_resp.raise_for_status()
        status_data = status_resp.json()
        print(
            f"[SMOKE] Poll #{poll_count}: "
            f"status={status_data.get('status')} progress={status_data.get('progress')}"
        )

        if status_data["status"] in {"SUCCEEDED", "FAILED"}:
            print(f"[SMOKE] Terminal status reached: {status_data['status']}")
            break
        time.sleep(2)
    else:
        print("[SMOKE] Timed out waiting for job completion")
        sys.exit(1)

    print("[SMOKE] Fetching final result...")
    result_resp = requests.get(f"{BASE_URL}/analysis/{job_id}/result", timeout=10)
    print(f"[SMOKE] GET /analysis/{{job_id}}/result -> {result_resp.status_code}")
    print("[SMOKE] Result payload:")
    print(result_resp.json())


if __name__ == "__main__":
    main()
