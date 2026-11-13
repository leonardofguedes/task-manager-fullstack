from app.application.ports import UserRepository
from app.domain.users import User


class UserService:
    """Read-only user directory, used to pick an assignee."""

    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def list_all(self) -> list[User]:
        return self._users.list_all()
