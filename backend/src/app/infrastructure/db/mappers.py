"""Translate between ORM rows and domain entities, so the domain never imports SQLAlchemy."""

from app.domain.notifications import Notification, NotificationKind
from app.domain.tasks import Task, TaskStatus
from app.domain.users import User
from app.infrastructure.db.models import NotificationModel, TaskModel, UserModel


def task_to_entity(row: TaskModel) -> Task:
    return Task(
        id=row.id,
        title=row.title,
        description=row.description,
        status=TaskStatus(row.status),
        due_date=row.due_date,
        owner_id=row.owner_id,
        assignee_id=row.assignee_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        completed_at=row.completed_at,
    )


def copy_task_to_row(task: Task, row: TaskModel) -> TaskModel:
    row.title = task.title
    row.description = task.description
    row.status = task.status.value
    row.due_date = task.due_date
    row.owner_id = task.owner_id
    row.assignee_id = task.assignee_id
    row.created_at = task.created_at
    row.updated_at = task.updated_at
    row.completed_at = task.completed_at
    return row


def user_to_entity(row: UserModel) -> User:
    return User(
        id=row.id,
        email=row.email,
        full_name=row.full_name,
        password_hash=row.password_hash,
        created_at=row.created_at,
    )


def notification_to_entity(row: NotificationModel) -> Notification:
    return Notification(
        id=row.id,
        user_id=row.user_id,
        task_id=row.task_id,
        kind=NotificationKind(row.kind),
        message=row.message,
        created_at=row.created_at,
    )
