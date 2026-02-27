"""Celery app configuration."""

from __future__ import annotations

import logging
import os

from celery import Celery
from celery.signals import after_setup_logger, after_setup_task_logger
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery = Celery("worker", broker=REDIS_URL, backend=REDIS_URL)
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_hijack_root_logger=False,
    worker_redirect_stdouts=False,
)

celery.autodiscover_tasks(["worker"])


def _suppress_noisy_loggers() -> None:
    logging.getLogger().setLevel(logging.WARNING)
    for name in (
        "celery",
        "celery.app.trace",
        "kombu",
        "amqp",
        "httpx",
        "httpcore",
        "openai",
        "mcp",
        "mcp.server.lowlevel.server",
    ):
        logging.getLogger(name).setLevel(logging.WARNING)


@after_setup_logger.connect
def _configure_celery_logger(logger: logging.Logger, *args, **kwargs) -> None:
    logger.setLevel(logging.WARNING)
    _suppress_noisy_loggers()


@after_setup_task_logger.connect
def _configure_celery_task_logger(logger: logging.Logger, *args, **kwargs) -> None:
    logger.setLevel(logging.WARNING)
    _suppress_noisy_loggers()
