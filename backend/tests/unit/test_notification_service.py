from datetime import UTC, date, datetime

import pytest

from app.application.notification_service import NotificationService
from app.domain.notifications import NotificationKind
from app.domain.tasks import Task, TaskStatus
from app.domain.users import User
from tests.fakes import (
    FakeClock,
    FakeUnitOfWork,
    InMemoryNotificationRepository,
    InMemoryTaskRepository,
    InMemoryUserRepository,
)

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
ALICE, BOB = 1, 2


@pytest.fixture
def tasks() -> InMemoryTaskRepository:
    return InMemoryTaskRepository()


@pytest.fixture
def notifications() -> InMemoryNotificationRepository:
    return InMemoryNotificationRepository()


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def service(
    tasks: InMemoryTaskRepository,
    notifications: InMemoryNotificationRepository,
    uow: FakeUnitOfWork,
) -> NotificationService:
    users = InMemoryUserRepository()
    users.add(User(None, "alice@example.com", "Alice", "x", NOW))
    users.add(User(None, "bob@example.com", "Bob", "x", NOW))
    return NotificationService(tasks, users, notifications, uow, FakeClock(NOW))


def add_task(tasks: InMemoryTaskRepository, **kwargs: object) -> Task:
    params: dict[str, object] = {"title": "Ship", "owner_id": ALICE, "now": NOW, **kwargs}
    return tasks.add(Task.new(**params))  # type: ignore[arg-type]


def test_notify_assignment_creates_notification(
    service: NotificationService, tasks: InMemoryTaskRepository, uow: FakeUnitOfWork
) -> None:
    task = add_task(tasks, assignee_id=BOB)
    assert task.id is not None

    created = service.notify_assignment(task.id, BOB)

    assert created is not None
    assert (created.user_id, created.task_id, created.kind) == (BOB, task.id, "assigned")
    assert created.message == 'You were assigned to "Ship"'
    assert uow.commits == 1


def test_notify_assignment_ignores_stale_assignee(
    service: NotificationService, tasks: InMemoryTaskRepository
) -> None:
    task = add_task(tasks, assignee_id=ALICE)
    assert task.id is not None

    assert service.notify_assignment(task.id, BOB) is None


def test_notify_assignment_ignores_deleted_task(service: NotificationService) -> None:
    assert service.notify_assignment(404, BOB) is None


def test_notify_overdue_targets_assignee_else_owner(
    service: NotificationService,
    tasks: InMemoryTaskRepository,
    notifications: InMemoryNotificationRepository,
) -> None:
    add_task(tasks, title="late, assigned", due_date=date(2026, 11, 1), assignee_id=BOB)
    add_task(tasks, title="late, unassigned", due_date=date(2026, 11, 2))
    add_task(tasks, title="late but done", due_date=date(2026, 11, 2), status=TaskStatus.DONE)
    add_task(tasks, title="due today", due_date=date(2026, 11, 12))

    count = service.notify_overdue()

    assert count == 2
    assert sorted((n.user_id, n.message) for n in notifications.rows) == [
        (ALICE, 'Task "late, unassigned" is overdue (due 2026-11-02)'),
        (BOB, 'Task "late, assigned" is overdue (due 2026-11-01)'),
    ]
    assert all(n.kind is NotificationKind.OVERDUE for n in notifications.rows)


def test_notify_overdue_is_idempotent(
    service: NotificationService, tasks: InMemoryTaskRepository
) -> None:
    add_task(tasks, due_date=date(2026, 11, 1))

    assert service.notify_overdue() == 1
    assert service.notify_overdue() == 0


def test_list_for_user_newest_first(
    service: NotificationService, tasks: InMemoryTaskRepository
) -> None:
    first = add_task(tasks, title="first", assignee_id=BOB)
    second = add_task(tasks, title="second", assignee_id=BOB)
    assert first.id is not None and second.id is not None
    service.notify_assignment(first.id, BOB)
    service._clock.advance(  # type: ignore[attr-defined]
        datetime(2026, 11, 12, 13, tzinfo=UTC) - NOW
    )
    service.notify_assignment(second.id, BOB)

    messages = [n.message for n in service.list_for_user(BOB)]

    assert messages == ['You were assigned to "second"', 'You were assigned to "first"']
