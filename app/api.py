# DIFF SUMMARY:
# - Kept POST /analysis request model as prompt only.
# - Removed API-side ticker extraction; API now enqueues prompt directly.
"""Minimal FastAPI endpoints for async-job-style analysis flow."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.db.engine import SessionLocal
from app.db.models import Job
from worker.tasks import run_analysis_task

router = APIRouter()
logger = logging.getLogger(__name__)


class AnalysisRequest(BaseModel):
    prompt: str

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        prompt = value.strip()
        if not prompt:
            raise ValueError("prompt must not be empty")
        if len(prompt) > 1000:
            raise ValueError("prompt must be at most 1000 characters")
        return prompt


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _serialize_job(job: Job) -> dict[str, Any]:
    return {
        "job_id": job.id,
        "status": job.status,
        "progress": job.progress,
        "error": job.error,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


@router.post("/analysis")
def create_analysis_job(payload: AnalysisRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    request_body = {"prompt": payload.prompt}
    job = Job(
        status="QUEUED",
        progress=0,
        input_json=json.dumps(request_body),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info(
        "create_analysis_job queued job_id=%s original_prompt=%r",
        job.id,
        payload.prompt,
    )
    run_analysis_task.delay(job.id)

    return {"job_id": job.id}


@router.get("/analysis/{job_id}")
def get_analysis_job(job_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return _serialize_job(job)


@router.get("/analysis/{job_id}/result")
def get_analysis_result(job_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status == "FAILED":
        return JSONResponse(status_code=409, content={"status": "FAILED", "error": job.error})
    if job.status != "SUCCEEDED":
        return JSONResponse(status_code=409, content={"status": job.status, "message": "not ready"})
    if not job.result_json:
        raise HTTPException(status_code=500, detail="result_json missing")

    try:
        parsed = json.loads(job.result_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="result_json invalid JSON") from exc

    if not isinstance(parsed, dict):
        raise HTTPException(status_code=500, detail="result_json must decode to an object")
    return parsed
