from typing import Any

from celery import Celery
from celery.signals import beat_init

from app.config import get_infra_settings

settings = get_infra_settings()

celery_app = Celery(
    "task_manager",
    broker=settings.redis_url,
    include=["app.infrastructure.worker.jobs"],
)
celery_app.conf.update(
    task_always_eager=settings.celery_task_always_eager,
    task_ignore_result=True,  # nobody reads job return values: no result backend needed
    # Ack on receipt (at-most-once) by default: re-running the assignment job after a crash
    # would duplicate the notification. The overdue scan opts into acks_late (safe to rerun).
    task_acks_late=False,
    worker_prefetch_multiplier=1,
    # Fail fast when Redis is down instead of blocking the API request that enqueues.
    broker_connection_timeout=2,
    broker_transport_options={
        "socket_connect_timeout": 2,
        "socket_timeout": 2,
        "max_retries": 1,  # kombu reconnect attempts when opening the publish channel
        "interval_start": 0,
        "interval_step": 0.5,
        "interval_max": 1,
    },
    task_publish_retry_policy={"max_retries": 2, "interval_start": 0, "interval_step": 0.5},
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
