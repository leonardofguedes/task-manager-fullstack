from app.application.ports import (
    Clock,
    NotificationRepository,
    TaskRepository,
    UnitOfWork,
    UserRepository,
)
from app.domain.ids import persisted_id
from app.domain.notifications import Notification, NotificationKind


class NotificationService:
    """Use cases run by the background worker, plus the inbox query for the API."""

    def __init__(
        self,
        tasks: TaskRepository,
        users: UserRepository,
        notifications: NotificationRepository,
        uow: UnitOfWork,
        clock: Clock,
    ) -> None:
        self._tasks = tasks
        self._users = users
        self._notifications = notifications
        self._uow = uow
        self._clock = clock

    def notify_assignment(self, task_id: int, assignee_id: int) -> Notification | None:
        task = self._tasks.get(task_id)
        # The job may run after the task was deleted or reassigned: then there is nothing to say.
        if task is None or task.assignee_id != assignee_id or self._users.get(assignee_id) is None:
            return None
        notification = self._notifications.add(
            Notification(
                id=None,
                user_id=assignee_id,
                task_id=task_id,
                kind=NotificationKind.ASSIGNED,
                message=f'You were assigned to "{task.title}"',
                created_at=self._clock.now(),
            )
        )
        self._uow.commit()
        return notification

    def notify_overdue(self) -> int:
        """Create one OVERDUE notification per overdue task (idempotent). Returns how many."""
        created = 0
        for task in self._tasks.list_overdue(self._clock.today()):
            task_id = persisted_id(task.id)
            if self._notifications.exists(task_id, NotificationKind.OVERDUE):
                continue
            self._notifications.add(
                Notification(
                    id=None,
                    user_id=task.assignee_id or task.owner_id,
                    task_id=task_id,
                    kind=NotificationKind.OVERDUE,
                    message=f'Task "{task.title}" is overdue (due {task.due_date:%Y-%m-%d})',
                    created_at=self._clock.now(),
                )
            )
            created += 1
        self._uow.commit()
        return created

    def list_for_user(self, user_id: int, limit: int = 20) -> list[Notification]:
        return self._notifications.list_for_user(user_id, limit)
