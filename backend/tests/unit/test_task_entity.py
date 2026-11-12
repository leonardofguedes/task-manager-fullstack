from datetime import UTC, date, datetime, timedelta

import pytest

from app.domain.errors import ValidationError
from app.domain.tasks import Task, TaskStatus

T0 = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
T2 = T0 + timedelta(hours=2)
TODAY = date(2026, 11, 12)


def make_task(**overrides: object) -> Task:
    params: dict[str, object] = {"title": "Write tests", "owner_id": 1, "now": T0}
    params.update(overrides)
    return Task.new(**params)  # type: ignore[arg-type]


def test_new_task_strips_title_and_defaults_to_todo() -> None:
    task = make_task(title="  Buy milk ")

    assert task.title == "Buy milk"
    assert task.status is TaskStatus.TODO
    assert task.completed_at is None
    assert task.created_at == T0
    assert task.updated_at == T0
    assert task.id is None


@pytest.mark.parametrize("title", ["", "   ", "x" * 201])
def test_title_blank_or_over_200_chars_raises(title: str) -> None:
    with pytest.raises(ValidationError):
        make_task(title=title)


def test_rename_validates_title() -> None:
    task = make_task()

    with pytest.raises(ValidationError):
        task.rename("  ", T1)


def test_description_over_2000_chars_raises() -> None:
    with pytest.raises(ValidationError):
        make_task(description="x" * 2001)


def test_new_task_created_as_done_has_completed_at() -> None:
    task = make_task(status=TaskStatus.DONE)

    assert task.completed_at == T0


def test_complete_sets_completed_at_and_reopen_clears_it() -> None:
    task = make_task()

    task.complete(T1)
    assert task.status is TaskStatus.DONE
    assert task.completed_at == T1

    task.change_status(TaskStatus.TODO, T2)
    assert task.completed_at is None
    assert task.updated_at == T2


def test_completing_twice_keeps_first_completion_time() -> None:
    task = make_task()
    task.complete(T1)

    task.complete(T2)

    assert task.completed_at == T1


@pytest.mark.parametrize(
    ("due_date", "status", "expected"),
    [
        (TODAY - timedelta(days=1), TaskStatus.TODO, True),
        (TODAY, TaskStatus.TODO, False),
        (TODAY - timedelta(days=1), TaskStatus.DONE, False),
        (None, TaskStatus.TODO, False),
    ],
)
def test_is_overdue(due_date: date | None, status: TaskStatus, expected: bool) -> None:
    task = make_task(due_date=due_date, status=status)

    assert task.is_overdue(TODAY) is expected


def test_permissions() -> None:
    task = make_task(owner_id=1, assignee_id=2)

    assert task.can_edit(1) and task.can_delete(1)
    assert task.can_edit(2) and not task.can_delete(2)
    assert not task.can_edit(3) and not task.can_delete(3)


def test_mutators_touch_updated_at() -> None:
    task = make_task()

    task.describe("details", T1)
    assert (task.description, task.updated_at) == ("details", T1)

    task.reschedule(TODAY, T2)
    assert task.due_date == TODAY

    task.assign(5, T2)
    assert task.assignee_id == 5
