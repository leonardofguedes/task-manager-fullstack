"""Ports: the interfaces the use cases depend on. Infrastructure provides the adapters."""

from __future__ import annotations

import builtins
from datetime import date, datetime
from typing import TYPE_CHECKING, Protocol

from app.application.pagination import Page, PageParams
from app.domain.notifications import Notification, NotificationKind
from app.domain.tasks import Task
from app.domain.users import User

if TYPE_CHECKING:
    from app.application.task_service import TaskFilters


class Clock(Protocol):
    def now(self) -> datetime: ...

    def today(self) -> date: ...


class TaskRepository(Protocol):
    def add(self, task: Task) -> Task: ...

    def get(self, task_id: int) -> Task | None: ...

    def update(self, task: Task) -> Task: ...

    def delete(self, task_id: int) -> None: ...

    def list(self, filters: TaskFilters, page: PageParams) -> Page[Task]: ...

    def list_overdue(self, today: date) -> builtins.list[Task]: ...


class UserRepository(Protocol):
    def add(self, user: User) -> User: ...

    def get(self, user_id: int) -> User | None: ...

    def get_by_email(self, email: str) -> User | None: ...

    def list_all(self) -> list[User]: ...


class NotificationRepository(Protocol):
    def add(self, notification: Notification) -> Notification: ...

    def list_for_user(self, user_id: int, limit: int) -> list[Notification]: ...

    def exists(self, task_id: int, kind: NotificationKind) -> bool: ...


class UnitOfWork(Protocol):
    def commit(self) -> None: ...


class PasswordHasher(Protocol):
    def hash(self, plain: str) -> str: ...

    def verify(self, plain: str, hashed: str) -> bool: ...


class TokenService(Protocol):
    def issue(self, user_id: int) -> str: ...

    def decode(self, token: str) -> int: ...


class NotificationDispatcher(Protocol):
    def task_assigned(self, task_id: int, assignee_id: int) -> None: ...
