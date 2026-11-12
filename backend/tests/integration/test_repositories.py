from datetime import UTC, date, datetime

import pytest
from sqlalchemy.orm import Session

from app.application.pagination import PageParams
from app.application.task_service import TaskFilters
from app.domain.notifications import Notification, NotificationKind
from app.domain.tasks import Task, TaskStatus
from app.domain.users import User
from app.infrastructure.repositories.notifications import SqlNotificationRepository
from app.infrastructure.repositories.tasks import SqlTaskRepository
from app.infrastructure.repositories.users import SqlUserRepository

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)


@pytest.fixture
def users(session: Session) -> SqlUserRepository:
    return SqlUserRepository(session)


@pytest.fixture
def tasks(session: Session) -> SqlTaskRepository:
    return SqlTaskRepository(session)


@pytest.fixture
def alice(users: SqlUserRepository) -> User:
    return users.add(User(None, "alice@example.com", "Alice", "hash", NOW))


@pytest.fixture
def bob(users: SqlUserRepository) -> User:
    return users.add(User(None, "bob@example.com", "Bob", "hash", NOW))


def new_task(owner: User, **kwargs: object) -> Task:
    assert owner.id is not None
    return Task.new(owner_id=owner.id, now=NOW, **{"title": "t", **kwargs})  # type: ignore[arg-type]


def test_task_roundtrip_preserves_fields(tasks: SqlTaskRepository, alice: User, bob: User) -> None:
    saved = tasks.add(
        new_task(
            alice,
            title="Ship it",
            description="details",
            due_date=date(2026, 11, 20),
            assignee_id=bob.id,
            status=TaskStatus.DONE,
        )
    )
    assert saved.id is not None

    loaded = tasks.get(saved.id)

    assert loaded == saved
    assert loaded.completed_at == NOW
    assert loaded.created_at.tzinfo is not None


def test_update_and_delete(tasks: SqlTaskRepository, alice: User) -> None:
    saved = tasks.add(new_task(alice))
    assert saved.id is not None
    saved.rename("renamed", NOW)

    tasks.update(saved)
    assert tasks.get(saved.id).title == "renamed"  # type: ignore[union-attr]

    tasks.delete(saved.id)
    assert tasks.get(saved.id) is None


def test_list_filters_and_pagination_match_in_memory_semantics(
    tasks: SqlTaskRepository, alice: User, bob: User
) -> None:
    tasks.add(new_task(alice, title="no due"))
    for day in (20, 10, 15):
        tasks.add(new_task(alice, title=f"due {day}", due_date=date(2026, 11, day)))
    tasks.add(new_task(alice, title="done", due_date=date(2026, 11, 16), status=TaskStatus.DONE))
    tasks.add(new_task(alice, title="bob's", due_date=date(2026, 11, 18), assignee_id=bob.id))

    everything = tasks.list(TaskFilters(), PageParams(limit=100))
    assert [t.title for t in everything.items] == [
        "due 10",
        "due 15",
        "done",
        "bob's",
        "due 20",
        "no due",
    ]

    ranged = tasks.list(
        TaskFilters(
            status=TaskStatus.TODO, due_after=date(2026, 11, 15), due_before=date(2026, 11, 20)
        ),
        PageParams(),
    )
    assert [t.title for t in ranged.items] == ["due 15", "bob's", "due 20"]

    assigned = tasks.list(TaskFilters(assignee_id=bob.id), PageParams())
    assert [t.title for t in assigned.items] == ["bob's"]

    page = tasks.list(TaskFilters(), PageParams(limit=2, offset=4))
    assert [t.title for t in page.items] == ["due 20", "no due"]
    assert page.total == 6

    past_end = tasks.list(TaskFilters(), PageParams(limit=2, offset=50))
    assert past_end.items == [] and past_end.total == 6


def test_list_overdue(tasks: SqlTaskRepository, alice: User) -> None:
    tasks.add(new_task(alice, title="late", due_date=date(2026, 11, 1)))
    tasks.add(new_task(alice, title="late but done", due_date=date(2026, 11, 1), status="done"))
    tasks.add(new_task(alice, title="today", due_date=date(2026, 11, 12)))

    overdue = tasks.list_overdue(date(2026, 11, 12))

    assert [t.title for t in overdue] == ["late"]


def test_user_get_by_email_and_list(users: SqlUserRepository, alice: User, bob: User) -> None:
    assert users.get_by_email("alice@example.com") == alice
    assert users.get_by_email("nobody@example.com") is None
    assert [u.email for u in users.list_all()] == ["alice@example.com", "bob@example.com"]


def test_notification_exists_and_list(
    session: Session, tasks: SqlTaskRepository, alice: User
) -> None:
    task = tasks.add(new_task(alice))
    assert task.id is not None and alice.id is not None
    repo = SqlNotificationRepository(session)

    assert not repo.exists(task.id, NotificationKind.OVERDUE)
    repo.add(Notification(None, alice.id, task.id, NotificationKind.OVERDUE, "late", NOW))

    assert repo.exists(task.id, NotificationKind.OVERDUE)
    assert not repo.exists(task.id, NotificationKind.ASSIGNED)
    assert [n.message for n in repo.list_for_user(alice.id, limit=10)] == ["late"]
