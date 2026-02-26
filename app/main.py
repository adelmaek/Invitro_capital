"""FastAPI app entrypoint."""

from __future__ import annotations

from fastapi import FastAPI

from app.api import router
from app.db.engine import init_db

app = FastAPI(title="Analysis Jobs API")
app.include_router(router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
