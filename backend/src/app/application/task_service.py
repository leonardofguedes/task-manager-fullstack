from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import TypedDict

from app.application.pagination import Page, PageParams
from app.application.ports import (
    Clock,
    NotificationDispatcher,
    TaskRepository,
    UnitOfWork,
    UserRepository,
)
from app.domain.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.domain.tasks import Task, TaskStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TaskFilters:
    status: TaskStatus | None = None
    due_before: date | None = None
    due_after: date | None = None
    assignee_id: int | None = None


@dataclass(frozen=True)
class TaskCreate:
    title: str
    description: str | None = None
    due_date: date | None = None
    assignee_id: int | None = None
    status: TaskStatus = TaskStatus.TODO


class TaskChanges(TypedDict, total=False):
    """PATCH payload: only the keys present are applied; an explicit None clears the field."""

    title: str
    description: str | None
    due_date: date | None
    assignee_id: int | None
    status: TaskStatus


class TaskService:
    def __init__(
        self,
        tasks: TaskRepository,
        users: UserRepository,
        uow: UnitOfWork,
        dispatcher: NotificationDispatcher,
        clock: Clock,
    ) -> None:
        self._tasks = tasks
        self._users = users
        self._uow = uow
        self._dispatcher = dispatcher
        self._clock = clock

    def create(self, actor_id: int, data: TaskCreate) -> Task:
        self._ensure_assignee_exists(data.assignee_id)
        task = Task.new(
            title=data.title,
            owner_id=actor_id,
            now=self._clock.now(),
            description=data.description,
            due_date=data.due_date,
            assignee_id=data.assignee_id,
            status=data.status,
        )
        saved = self._tasks.add(task)
        self._uow.commit()
        self._notify_if_newly_assigned(saved, previous_assignee=None, actor_id=actor_id)
        return saved

    def get(self, actor_id: int, task_id: int) -> Task:
        return self._load(task_id)

    def list(self, actor_id: int, filters: TaskFilters, page: PageParams) -> Page[Task]:
        if filters.due_after and filters.due_before and filters.due_after > filters.due_before:
            raise ValidationError("due_after must be on or before due_before")
        return self._tasks.list(filters, page)

    def update(self, actor_id: int, task_id: int, changes: TaskChanges) -> Task:
        task = self._load(task_id)
        if not task.can_edit(actor_id):
            raise PermissionDeniedError("only the owner or the assignee can edit this task")
        previous_assignee = task.assignee_id
        now = self._clock.now()

        if "title" in changes:
            task.rename(changes["title"], now)
        if "description" in changes:
            task.describe(changes["description"], now)
        if "due_date" in changes:
            task.reschedule(changes["due_date"], now)
        if "status" in changes:
            task.change_status(changes["status"], now)
        if "assignee_id" in changes:
            self._ensure_assignee_exists(changes["assignee_id"])
            task.assign(changes["assignee_id"], now)

        saved = self._tasks.update(task)
        self._uow.commit()
        self._notify_if_newly_assigned(saved, previous_assignee, actor_id)
        return saved

    def complete(self, actor_id: int, task_id: int) -> Task:
        return self.update(actor_id, task_id, {"status": TaskStatus.DONE})

    def delete(self, actor_id: int, task_id: int) -> None:
        task = self._load(task_id)
        if not task.can_delete(actor_id):
            raise PermissionDeniedError("only the owner can delete this task")
        self._tasks.delete(task_id)
        self._uow.commit()

    def _load(self, task_id: int) -> Task:
        task = self._tasks.get(task_id)
        if task is None:
            raise NotFoundError("task", task_id)
        return task

    def _ensure_assignee_exists(self, assignee_id: int | None) -> None:
        if assignee_id is not None and self._users.get(assignee_id) is None:
            raise ValidationError("assignee not found")

    def _notify_if_newly_assigned(
        self, task: Task, previous_assignee: int | None, actor_id: int
    ) -> None:
        # Called only after commit, so the worker never races an uncommitted row.
        assignee = task.assignee_id
        if assignee is None or assignee in (previous_assignee, actor_id):
            return
        assert task.id is not None
        try:
            self._dispatcher.task_assigned(task.id, assignee)
        except Exception:
            # The task is already committed: failing the request now would make the client
            # retry and create a duplicate. A lost notification is the lesser evil (an
            # outbox table would remove it entirely).
            logger.warning(
                "could not enqueue assignment notification task_id=%s assignee_id=%s",
                task.id,
                assignee,
                exc_info=True,
            )
