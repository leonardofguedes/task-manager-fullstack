from __future__ import annotations

import builtins
from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.application.pagination import Page, PageParams
from app.application.task_service import TaskFilters
from app.domain.ids import persisted_id
from app.domain.tasks import Task, TaskStatus
from app.infrastructure.db.mappers import copy_task_to_row, task_to_entity
from app.infrastructure.db.models import TaskModel


class SqlTaskRepository:
    """TaskRepository adapter. Flushes but never commits: the unit of work owns the transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, task: Task) -> Task:
        row = copy_task_to_row(task, TaskModel())
        self._session.add(row)
        self._session.flush()
        return task_to_entity(row)

    def get(self, task_id: int) -> Task | None:
        row = self._session.get(TaskModel, task_id)
        return task_to_entity(row) if row else None

    def update(self, task: Task) -> Task:
        row = self._session.get_one(TaskModel, persisted_id(task.id))
        copy_task_to_row(task, row)
        self._session.flush()
        return task_to_entity(row)

    def delete(self, task_id: int) -> None:
        row = self._session.get(TaskModel, task_id)
        if row is not None:
            self._session.delete(row)
            self._session.flush()

    def list(self, filters: TaskFilters, page: PageParams) -> Page[Task]:
        query = _apply_filters(select(TaskModel), filters)
        total = self._session.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = self._session.scalars(
            query.order_by(TaskModel.due_date.is_(None), TaskModel.due_date, TaskModel.id)
            .limit(page.limit)
            .offset(page.offset)
        )
        return Page(
            items=[task_to_entity(r) for r in rows],
            total=total,
            limit=page.limit,
            offset=page.offset,
        )

    def list_overdue(self, today: date) -> builtins.list[Task]:
        rows = self._session.scalars(
            select(TaskModel)
            .where(TaskModel.due_date < today, TaskModel.status != TaskStatus.DONE.value)
            .order_by(TaskModel.id)
        )
        return [task_to_entity(r) for r in rows]


def _apply_filters(query: Select[TaskModel], f: TaskFilters) -> Select[TaskModel]:
    if f.status is not None:
        query = query.where(TaskModel.status == f.status.value)
    if f.assignee_id is not None:
        query = query.where(TaskModel.assignee_id == f.assignee_id)
    if f.due_after is not None:
        query = query.where(TaskModel.due_date >= f.due_after)
    if f.due_before is not None:
        query = query.where(TaskModel.due_date <= f.due_before)
    return query
