from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import ClockDep, CurrentUser, SessionDep
from app.api.schemas import NotificationOut
from app.application.notification_service import NotificationService
from app.infrastructure.repositories.notifications import SqlNotificationRepository
from app.infrastructure.repositories.tasks import SqlTaskRepository
from app.infrastructure.repositories.uow import SqlUnitOfWork
from app.infrastructure.repositories.users import SqlUserRepository

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(
    user: CurrentUser,
    session: SessionDep,
    clock: ClockDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[NotificationOut]:
    """The current user's notifications, newest first."""
    assert user.id is not None
    service = NotificationService(
        SqlTaskRepository(session),
        SqlUserRepository(session),
        SqlNotificationRepository(session),
        SqlUnitOfWork(session),
        clock,
    )
    return [NotificationOut.model_validate(n) for n in service.list_for_user(user.id, limit)]
