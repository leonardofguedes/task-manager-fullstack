from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from app.domain.errors import ValidationError

TITLE_MAX_LENGTH = 200
DESCRIPTION_MAX_LENGTH = 2000


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


@dataclass
class Task:
    id: int | None
    title: str
    description: str | None
    status: TaskStatus
    due_date: date | None
    owner_id: int
    assignee_id: int | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    @classmethod
    def new(
        cls,
        *,
        title: str,
        owner_id: int,
        now: datetime,
        description: str | None = None,
        due_date: date | None = None,
        assignee_id: int | None = None,
        status: TaskStatus = TaskStatus.TODO,
    ) -> Task:
        task = cls(
            id=None,
            title=_clean_title(title),
            description=_clean_description(description),
            status=TaskStatus.TODO,
            due_date=due_date,
            owner_id=owner_id,
            assignee_id=assignee_id,
            created_at=now,
            updated_at=now,
        )
        task.change_status(status, now)
        return task

    def rename(self, title: str, now: datetime) -> None:
        self.title = _clean_title(title)
        self.updated_at = now

    def describe(self, description: str | None, now: datetime) -> None:
        self.description = _clean_description(description)
        self.updated_at = now

    def reschedule(self, due_date: date | None, now: datetime) -> None:
        self.due_date = due_date
        self.updated_at = now

    def assign(self, assignee_id: int | None, now: datetime) -> None:
        self.assignee_id = assignee_id
        self.updated_at = now

    def change_status(self, status: TaskStatus | str, now: datetime) -> None:
        try:
            status = TaskStatus(status)
        except ValueError as exc:
            raise ValidationError(f"unknown status: {status!r}") from exc
        if status is TaskStatus.DONE and self.completed_at is None:
            self.completed_at = now
        elif status is not TaskStatus.DONE:
            self.completed_at = None
        self.status = status
        self.updated_at = now

    def complete(self, now: datetime) -> None:
        self.change_status(TaskStatus.DONE, now)

    def is_overdue(self, today: date) -> bool:
        return (
            self.due_date is not None and self.due_date < today and self.status != TaskStatus.DONE
        )

    def can_edit(self, user_id: int) -> bool:
        return user_id in (self.owner_id, self.assignee_id)

    def can_delete(self, user_id: int) -> bool:
        return user_id == self.owner_id


def _clean_title(title: str) -> str:
    cleaned = title.strip()
    if not cleaned:
        raise ValidationError("title must not be blank")
    if len(cleaned) > TITLE_MAX_LENGTH:
        raise ValidationError(f"title must be at most {TITLE_MAX_LENGTH} characters")
    return cleaned


def _clean_description(description: str | None) -> str | None:
    if description is None:
        return None
    cleaned = description.strip()
    if len(cleaned) > DESCRIPTION_MAX_LENGTH:
        raise ValidationError(f"description must be at most {DESCRIPTION_MAX_LENGTH} characters")
    return cleaned or None
