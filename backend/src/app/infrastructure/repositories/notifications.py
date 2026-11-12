from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.domain.notifications import Notification, NotificationKind
from app.infrastructure.db.mappers import notification_to_entity
from app.infrastructure.db.models import NotificationModel


class SqlNotificationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, notification: Notification) -> Notification:
        row = NotificationModel(
            user_id=notification.user_id,
            task_id=notification.task_id,
            kind=notification.kind.value,
            message=notification.message,
            created_at=notification.created_at,
        )
        self._session.add(row)
        self._session.flush()
        return notification_to_entity(row)

    def list_for_user(self, user_id: int, limit: int) -> list[Notification]:
        rows = self._session.scalars(
            select(NotificationModel)
            .where(NotificationModel.user_id == user_id)
            .order_by(NotificationModel.created_at.desc(), NotificationModel.id.desc())
            .limit(limit)
        )
        return [notification_to_entity(r) for r in rows]

    def exists(self, task_id: int, kind: NotificationKind) -> bool:
        query = select(
            exists().where(
                NotificationModel.task_id == task_id, NotificationModel.kind == kind.value
            )
        )
        return bool(self._session.scalar(query))
