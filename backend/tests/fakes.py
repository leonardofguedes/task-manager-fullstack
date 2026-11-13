"""In-memory implementations of the application ports, used by unit tests."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta

from app.application.pagination import Page, PageParams
from app.application.task_service import TaskFilters
from app.domain.errors import AuthenticationError
from app.domain.notifications import Notification, NotificationKind
from app.domain.tasks import Task
from app.domain.users import User


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current

    def today(self) -> date:
        return self.current.date()

    def advance(self, delta: timedelta) -> None:
        self.current += delta


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self.rows: dict[int, Task] = {}
        self._next_id = 1

    def add(self, task: Task) -> Task:
        stored = replace(task, id=self._next_id)
        self._next_id += 1
        self.rows[stored.id] = stored  # type: ignore[index]
        return replace(stored)

    def get(self, task_id: int) -> Task | None:
        task = self.rows.get(task_id)
        return replace(task) if task else None

    def update(self, task: Task) -> Task:
        assert task.id is not None and task.id in self.rows
        self.rows[task.id] = replace(task)
        return replace(task)

    def delete(self, task_id: int) -> None:
        self.rows.pop(task_id, None)

    def list(self, filters: TaskFilters, page: PageParams) -> Page[Task]:
        matches = [t for t in self.rows.values() if _matches(t, filters)]
        matches.sort(key=lambda t: (t.due_date is None, t.due_date or date.min, t.id))
        window = matches[page.offset : page.offset + page.limit]
        return Page(
            items=[replace(t) for t in window],
            total=len(matches),
            limit=page.limit,
            offset=page.offset,
        )

    def list_overdue(self, today: date) -> list[Task]:
        return [replace(t) for t in self.rows.values() if t.is_overdue(today)]


def _matches(task: Task, f: TaskFilters) -> bool:
    if f.status is not None and task.status != f.status:
        return False
    if f.assignee_id is not None and task.assignee_id != f.assignee_id:
        return False
    if f.due_after is not None and (task.due_date is None or task.due_date < f.due_after):
        return False
    return not (
        f.due_before is not None and (task.due_date is None or task.due_date > f.due_before)
    )


class InMemoryUserRepository:
    def __init__(self) -> None:
        self.rows: dict[int, User] = {}
        self._next_id = 1

    def add(self, user: User) -> User:
        stored = replace(user, id=self._next_id)
        self._next_id += 1
        self.rows[stored.id] = stored  # type: ignore[index]
        return replace(stored)

    def get(self, user_id: int) -> User | None:
        user = self.rows.get(user_id)
        return replace(user) if user else None

    def get_by_email(self, email: str) -> User | None:
        return next((replace(u) for u in self.rows.values() if u.email == email), None)

    def list_all(self) -> list[User]:
        return [replace(u) for u in self.rows.values()]


class InMemoryNotificationRepository:
    def __init__(self) -> None:
        self.rows: list[Notification] = []

    def add(self, notification: Notification) -> Notification:
        stored = replace(notification, id=len(self.rows) + 1)
        self.rows.append(stored)
        return stored

    def list_for_user(self, user_id: int, limit: int) -> list[Notification]:
        mine = [n for n in self.rows if n.user_id == user_id]
        return sorted(mine, key=lambda n: (n.created_at, n.id or 0), reverse=True)[:limit]

    def exists(self, task_id: int, kind: NotificationKind) -> bool:
        return any(n.task_id == task_id and n.kind == kind for n in self.rows)


@dataclass
class FakeUnitOfWork:
    commits: int = 0

    def commit(self) -> None:
        self.commits += 1


@dataclass
class RecordingDispatcher:
    uow: FakeUnitOfWork | None = None
    calls: list[tuple[int, int]] = field(default_factory=list)
    commits_at_call: list[int] = field(default_factory=list)

    def task_assigned(self, task_id: int, assignee_id: int) -> None:
        self.calls.append((task_id, assignee_id))
        self.commits_at_call.append(self.uow.commits if self.uow else -1)


class PlainHasher:
    def __init__(self) -> None:
        self.checks = 0  # real and dummy verifications, to assert constant work per login

    def hash(self, plain: str) -> str:
        return f"hashed:{plain}"

    def verify(self, plain: str, hashed: str) -> bool:
        self.checks += 1
        return hashed == f"hashed:{plain}"

    def verify_dummy(self, plain: str) -> None:
        self.checks += 1


class FakeTokenService:
    def issue(self, user_id: int) -> str:
        return f"token-{user_id}"

    def decode(self, token: str) -> int:
        prefix = "token-"
        if not token.startswith(prefix) or not token[len(prefix) :].isdigit():
            raise AuthenticationError("invalid token")
        return int(token[len(prefix) :])


@dataclass
class BrokenDispatcher:
    """Simulates the message broker being down at enqueue time."""

    attempts: int = 0

    def task_assigned(self, task_id: int, assignee_id: int) -> None:
        self.attempts += 1
        raise ConnectionError("broker unreachable")
