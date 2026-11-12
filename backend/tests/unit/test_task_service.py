from datetime import UTC, date, datetime

import pytest

from app.application.pagination import PageParams
from app.application.task_service import TaskCreate, TaskFilters, TaskService
from app.domain.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.domain.tasks import TaskStatus
from app.domain.users import User
from tests.fakes import (
    FakeClock,
    FakeUnitOfWork,
    InMemoryTaskRepository,
    InMemoryUserRepository,
    RecordingDispatcher,
)

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
ALICE, BOB, CAROL = 1, 2, 3


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def dispatcher(uow: FakeUnitOfWork) -> RecordingDispatcher:
    return RecordingDispatcher(uow=uow)


@pytest.fixture
def tasks() -> InMemoryTaskRepository:
    return InMemoryTaskRepository()


@pytest.fixture
def service(
    tasks: InMemoryTaskRepository, uow: FakeUnitOfWork, dispatcher: RecordingDispatcher
) -> TaskService:
    users = InMemoryUserRepository()
    for name in ("alice", "bob", "carol"):
        users.add(User(None, f"{name}@example.com", name.title(), "x", NOW))
    return TaskService(tasks, users, uow, dispatcher, FakeClock(NOW))


def test_create_sets_owner_and_commits(service: TaskService, uow: FakeUnitOfWork) -> None:
    task = service.create(ALICE, TaskCreate(title="Plan sprint"))

    assert task.id is not None
    assert task.owner_id == ALICE
    assert uow.commits == 1


def test_create_with_unknown_assignee_raises_validation(service: TaskService) -> None:
    with pytest.raises(ValidationError, match="assignee not found"):
        service.create(ALICE, TaskCreate(title="x", assignee_id=99))


def test_create_with_assignee_dispatches_after_commit(
    service: TaskService, dispatcher: RecordingDispatcher
) -> None:
    task = service.create(ALICE, TaskCreate(title="x", assignee_id=BOB))

    assert dispatcher.calls == [(task.id, BOB)]
    assert dispatcher.commits_at_call == [1]


def test_reassigning_to_same_user_does_not_dispatch(
    service: TaskService, dispatcher: RecordingDispatcher
) -> None:
    task = service.create(ALICE, TaskCreate(title="x", assignee_id=BOB))
    assert task.id is not None

    service.update(ALICE, task.id, {"assignee_id": BOB, "title": "renamed"})

    assert len(dispatcher.calls) == 1


def test_self_assignment_does_not_dispatch(
    service: TaskService, dispatcher: RecordingDispatcher
) -> None:
    service.create(ALICE, TaskCreate(title="x", assignee_id=ALICE))

    assert dispatcher.calls == []


def test_get_unknown_task_raises_not_found(service: TaskService) -> None:
    with pytest.raises(NotFoundError):
        service.get(ALICE, 404)


def test_update_by_stranger_raises_permission_denied(service: TaskService) -> None:
    task = service.create(ALICE, TaskCreate(title="x", assignee_id=BOB))
    assert task.id is not None

    with pytest.raises(PermissionDeniedError):
        service.update(CAROL, task.id, {"title": "hijack"})


def test_update_by_assignee_allowed(service: TaskService) -> None:
    task = service.create(ALICE, TaskCreate(title="x", assignee_id=BOB))
    assert task.id is not None

    updated = service.update(BOB, task.id, {"status": TaskStatus.IN_PROGRESS})

    assert updated.status is TaskStatus.IN_PROGRESS


def test_update_with_explicit_none_clears_due_date(service: TaskService) -> None:
    task = service.create(ALICE, TaskCreate(title="x", due_date=date(2026, 12, 1)))
    assert task.id is not None

    updated = service.update(ALICE, task.id, {"due_date": None})

    assert updated.due_date is None


def test_update_with_unknown_assignee_raises_validation(service: TaskService) -> None:
    task = service.create(ALICE, TaskCreate(title="x"))
    assert task.id is not None

    with pytest.raises(ValidationError, match="assignee not found"):
        service.update(ALICE, task.id, {"assignee_id": 99})


def test_delete_by_assignee_raises_permission_denied(service: TaskService) -> None:
    task = service.create(ALICE, TaskCreate(title="x", assignee_id=BOB))
    assert task.id is not None

    with pytest.raises(PermissionDeniedError):
        service.delete(BOB, task.id)


def test_delete_by_owner_removes(service: TaskService) -> None:
    task = service.create(ALICE, TaskCreate(title="x"))
    assert task.id is not None

    service.delete(ALICE, task.id)

    with pytest.raises(NotFoundError):
        service.get(ALICE, task.id)


def test_complete_marks_done(service: TaskService) -> None:
    task = service.create(ALICE, TaskCreate(title="x"))
    assert task.id is not None

    done = service.complete(ALICE, task.id)

    assert done.status is TaskStatus.DONE
    assert done.completed_at == NOW


def test_list_filters_status_and_due_range_inclusive(service: TaskService) -> None:
    for day in (10, 15, 20):
        service.create(ALICE, TaskCreate(title=f"due {day}", due_date=date(2026, 11, day)))
    service.create(
        ALICE, TaskCreate(title="done", due_date=date(2026, 11, 16), status=TaskStatus.DONE)
    )

    page = service.list(
        ALICE,
        TaskFilters(
            status=TaskStatus.TODO, due_after=date(2026, 11, 15), due_before=date(2026, 11, 20)
        ),
        PageParams(),
    )

    assert [t.title for t in page.items] == ["due 15", "due 20"]


def test_list_rejects_inverted_due_range(service: TaskService) -> None:
    with pytest.raises(ValidationError):
        service.list(
            ALICE,
            TaskFilters(due_after=date(2026, 11, 20), due_before=date(2026, 11, 10)),
            PageParams(),
        )


def test_list_paginates_with_total(service: TaskService) -> None:
    for i in range(25):
        service.create(ALICE, TaskCreate(title=f"task {i}"))

    page = service.list(ALICE, TaskFilters(), PageParams(limit=10, offset=20))

    assert len(page.items) == 5
    assert page.total == 25
    assert (page.limit, page.offset) == (10, 20)
