# DIFF SUMMARY:
# - Updated POST payload to prompt-based request body.
"""Async API smoke test for Celery-backed analysis jobs.

Requires:
1) redis-server
2) uvicorn app.main:app --reload
3) celery -A worker.celery_app.celery worker --loglevel=INFO
"""

from __future__ import annotations

import sys
import time

import requests

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT_SECONDS = 60


def main() -> None:
    payload = {"prompt": "Analyze the company whose ticker GOOGL. Return only JSON."}
    print(f"POST /analysis {payload}")
    post_resp = requests.post(f"{BASE_URL}/analysis", json=payload, timeout=10)
    post_resp.raise_for_status()
    job_id = post_resp.json()["job_id"]
    print(f"job_id={job_id}")

    deadline = time.time() + TIMEOUT_SECONDS
    while time.time() < deadline:
        status_resp = requests.get(f"{BASE_URL}/analysis/{job_id}", timeout=10)
        status_resp.raise_for_status()
        status_data = status_resp.json()
        print(f"status={status_data['status']} progress={status_data['progress']}")

        if status_data["status"] in {"SUCCEEDED", "FAILED"}:
            break
        time.sleep(2)
    else:
        print("Timed out waiting for job completion")
        sys.exit(1)

    result_resp = requests.get(f"{BASE_URL}/analysis/{job_id}/result", timeout=10)
    print(f"GET /analysis/{{job_id}}/result -> {result_resp.status_code}")
    print(result_resp.json())


if __name__ == "__main__":
    main()
