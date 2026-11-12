from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.api.schemas import UserOut
from app.infrastructure.repositories.users import SqlUserRepository

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.get("")
def list_users(_: CurrentUser, session: SessionDep) -> list[UserOut]:
    """All users, used by the frontend to pick an assignee."""
    return [UserOut.model_validate(u) for u in SqlUserRepository(session).list_all()]
