"""Celery jobs. Each job opens its own DB session and runs a use case; it receives ids, not
objects, so it always works on fresh data."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.application.notification_service import NotificationService
from app.config import get_infra_settings
from app.infrastructure.clock import SystemClock
from app.infrastructure.db.session import make_engine, make_session_factory
from app.infrastructure.repositories.notifications import SqlNotificationRepository
from app.infrastructure.repositories.tasks import SqlTaskRepository
from app.infrastructure.repositories.uow import SqlUnitOfWork
from app.infrastructure.repositories.users import SqlUserRepository
from app.infrastructure.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return make_session_factory(make_engine(get_infra_settings().database_url))


@contextmanager
def notification_service() -> Iterator[NotificationService]:
    with get_session_factory()() as session:
        yield NotificationService(
            SqlTaskRepository(session),
            SqlUserRepository(session),
            SqlNotificationRepository(session),
            SqlUnitOfWork(session),
            SystemClock(),
        )


@celery_app.task(  # type: ignore[untyped-decorator]
    autoretry_for=(OperationalError,), max_retries=3, retry_backoff=True
)
def send_assignment_notification(task_id: int, assignee_id: int) -> bool:
    with notification_service() as service:
        notification = service.notify_assignment(task_id, assignee_id)
    logger.info(
        "assignment notification task_id=%s assignee_id=%s sent=%s",
        task_id,
        assignee_id,
        notification is not None,
    )
    return notification is not None


@celery_app.task(  # type: ignore[untyped-decorator]
    autoretry_for=(OperationalError,), max_retries=3, retry_backoff=True
)
def scan_overdue_tasks() -> int:
    with notification_service() as service:
        created = service.notify_overdue()
    logger.info("overdue scan created %s notification(s)", created)
    return created
