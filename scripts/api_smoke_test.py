# DIFF SUMMARY:
# - Updated POST payload to prompt-based request body.
"""API smoke test.

Run server first:
    uvicorn app.main:app --reload

Then run:
    python scripts/api_smoke_test.py
"""

from __future__ import annotations

import sys
import time

try:
    import requests
except ImportError:
    print("requests is not installed. Run: pip install -r requirements.txt")
    raise


BASE_URL = "http://127.0.0.1:8000"


def main() -> None:
    print("[SMOKE] Step 1/3: Sending POST /analysis")
    try:
        post_resp = requests.post(
            f"{BASE_URL}/analysis",
            json={"prompt": "Analyze the company whose ticker AAPL. Return only JSON."},
            timeout=5,
        )
    except requests.RequestException as exc:
        print(f"Server not reachable at {BASE_URL}: {exc}")
        return

    post_resp.raise_for_status()
    post_data = post_resp.json()
    job_id = post_data["job_id"]
    print(f"[SMOKE] Job created: job_id={job_id}")

    print("[SMOKE] Step 2/3: Polling status")
    for attempt in range(5):
        status_resp = requests.get(f"{BASE_URL}/analysis/{job_id}", timeout=5)
        status_resp.raise_for_status()
        status_data = status_resp.json()
        print(
            f"[SMOKE] Poll #{attempt + 1}: "
            f"status={status_data.get('status')} progress={status_data.get('progress')}"
        )
        if status_data.get("status") == "SUCCEEDED":
            print("[SMOKE] Terminal status reached: SUCCEEDED")
            break
        time.sleep(0.5)
    else:
        print("[SMOKE] Job did not reach SUCCEEDED in time")
        sys.exit(1)

    print("[SMOKE] Step 3/3: Fetching final result")
    result_resp = requests.get(f"{BASE_URL}/analysis/{job_id}/result", timeout=5)
    result_resp.raise_for_status()
    print(f"[SMOKE] GET /analysis/{{job_id}}/result -> {result_resp.json()}")


if __name__ == "__main__":
    main()
