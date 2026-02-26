"""Celery tasks for background analysis execution."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Ensure project root is importable when Celery is launched via console script.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.service import run_analysis
from app.db.crud import get_job, update_job
from app.db.engine import init_db
from worker.celery_app import celery


def _normalize_result_json(result: Any) -> str:
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            return json.dumps({"output": result})
        return json.dumps(parsed)
    return json.dumps(result)


def _run_analysis_with_real_stdio(ticker: str) -> Any:
    """Celery may replace stdio with logging proxies that lack fileno()."""
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    original_stdin = sys.stdin
    try:
        if getattr(sys, "__stdout__", None) is not None:
            sys.stdout = sys.__stdout__
        if getattr(sys, "__stderr__", None) is not None:
            sys.stderr = sys.__stderr__
        if getattr(sys, "__stdin__", None) is not None:
            sys.stdin = sys.__stdin__
        return asyncio.run(run_analysis(ticker=ticker))
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        sys.stdin = original_stdin


@celery.task(name="worker.run_analysis_task")
def run_analysis_task(job_id: str) -> None:
    init_db()
    job = get_job(job_id)
    if job is None:
        return

    try:
        update_job(job_id, status="RUNNING", progress=5, error=None)

        try:
            payload = json.loads(job.input_json)
        except json.JSONDecodeError:
            update_job(job_id, status="FAILED", progress=100, error="invalid input_json")
            return

        ticker = payload.get("ticker") if isinstance(payload, dict) else None
        if not ticker:
            update_job(job_id, status="FAILED", progress=100, error="ticker missing")
            return

        result = _run_analysis_with_real_stdio(ticker=ticker)
        result_json = _normalize_result_json(result)
        update_job(
            job_id,
            status="SUCCEEDED",
            progress=100,
            result_json=result_json,
            error=None,
        )
    except Exception as exc:
        update_job(job_id, status="FAILED", progress=100, error=str(exc))
