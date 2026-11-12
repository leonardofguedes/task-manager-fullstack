from typing import Any

from celery import Celery
from celery.signals import beat_init

from app.config import get_infra_settings

settings = get_infra_settings()

celery_app = Celery(
    "task_manager",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.infrastructure.worker.jobs"],
)
celery_app.conf.update(
    task_always_eager=settings.celery_task_always_eager,
    task_acks_late=True,  # a job is re-delivered if the worker dies mid-way
    worker_prefetch_multiplier=1,
    timezone="UTC",
    beat_schedule={
        "scan-overdue-tasks": {
            "task": "app.infrastructure.worker.jobs.scan_overdue_tasks",
            "schedule": settings.overdue_scan_minutes * 60.0,
        }
    },
)


@beat_init.connect  # type: ignore[untyped-decorator]
def scan_once_on_startup(sender: Any, **_: Any) -> None:
    """Interval schedules first fire after one interval; run one scan right away instead."""
    sender.app.send_task("app.infrastructure.worker.jobs.scan_overdue_tasks")
