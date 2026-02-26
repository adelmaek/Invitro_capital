"""Run a minimal SQLite jobs-table smoke test.

Usage:
    python scripts/db_smoke_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import create_job, get_job, init_db, update_job


def print_job_state(label: str, job_id: str) -> None:
    job = get_job(job_id)
    if job is None:
        print(f"{label}: job not found")
        return
    print(
        f"{label}: id={job.id} status={job.status} progress={job.progress} "
        f"result_json={job.result_json}"
    )


def main() -> None:
    init_db()

    job = create_job({"query": "Apple"})
    print(f"created job id={job.id}")

    print_job_state("read", job.id)

    update_job(job.id, status="RUNNING", progress=10)
    print_job_state("running", job.id)

    update_job(job.id, status="SUCCEEDED", progress=100, result_json="{}")
    print_job_state("done", job.id)


if __name__ == "__main__":
    main()
