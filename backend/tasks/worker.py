"""Celery worker configuration for Cortex async tasks."""

from celery import Celery

from backend.config import settings

app = Celery(
    "cortex",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
