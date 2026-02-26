"""Minimal CRUD helpers for jobs."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select

from .engine import SessionLocal
from .models import Job


def _to_json(value: Any) -> str:
    return json.dumps(value)


def create_job(input_dict: dict) -> Job:
    with SessionLocal() as session:
        job = Job(status="QUEUED", progress=0, input_json=_to_json(input_dict))
        session.add(job)
        session.commit()
        session.refresh(job)
        return job


def get_job(job_id: str) -> Job | None:
    with SessionLocal() as session:
        return session.get(Job, job_id)


def update_job(job_id: str, **fields: Any) -> Job | None:
    with SessionLocal() as session:
        job = session.get(Job, job_id)
        if job is None:
            return None

        if "input_dict" in fields:
            fields["input_json"] = _to_json(fields.pop("input_dict"))
        if "result_json" in fields and isinstance(fields["result_json"], (dict, list)):
            fields["result_json"] = _to_json(fields["result_json"])

        for key, value in fields.items():
            if hasattr(job, key):
                setattr(job, key, value)

        job.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(job)
        return job


def list_jobs(limit: int = 20) -> list[Job]:
    with SessionLocal() as session:
        stmt = select(Job).order_by(Job.created_at.desc()).limit(limit)
        return list(session.scalars(stmt).all())
