from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUserId, NotificationServiceDep
from app.api.schemas import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(
    user_id: CurrentUserId,
    service: NotificationServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[NotificationOut]:
    """The current user's notifications, newest first."""
    return [NotificationOut.model_validate(n) for n in service.list_for_user(user_id, limit)]
