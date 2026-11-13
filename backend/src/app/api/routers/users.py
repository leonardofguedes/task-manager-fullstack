from fastapi import APIRouter

from app.api.deps import CurrentUser, UserServiceDep
from app.api.schemas import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.get("")
def list_users(_: CurrentUser, users: UserServiceDep) -> list[UserOut]:
    """All users, used by the frontend to pick an assignee."""
    return [UserOut.model_validate(u) for u in users.list_all()]
