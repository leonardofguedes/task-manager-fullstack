from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.domain.notifications import NotificationKind
from app.domain.tasks import Task, TaskStatus


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=100)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    due_date: date | None = None
    assignee_id: int | None = None
    status: TaskStatus = TaskStatus.TODO


class TaskPatch(BaseModel):
    """Partial update: omitted fields are untouched, `null` clears nullable fields."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    due_date: date | None = None
    assignee_id: int | None = None
    status: TaskStatus | None = None

    @model_validator(mode="after")
    def _reject_null_required_fields(self) -> "TaskPatch":
        for name in ("title", "status"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class TaskOut(BaseModel):
    id: int
    title: str
    description: str | None
    status: TaskStatus
    due_date: date | None
    owner_id: int
    assignee_id: int | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    is_overdue: bool

    @classmethod
    def from_entity(cls, task: Task, today: date) -> "TaskOut":
        assert task.id is not None
        return cls(
            id=task.id,
            title=task.title,
            description=task.description,
            status=task.status,
            due_date=task.due_date,
            owner_id=task.owner_id,
            assignee_id=task.assignee_id,
            created_at=task.created_at,
            updated_at=task.updated_at,
            completed_at=task.completed_at,
            is_overdue=task.is_overdue(today),
        )


class TaskPage(BaseModel):
    items: list[TaskOut]
    total: int
    limit: int
    offset: int


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    kind: NotificationKind
    message: str
    created_at: datetime
