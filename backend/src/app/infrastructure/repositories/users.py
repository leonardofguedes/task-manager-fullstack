from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.users import User
from app.infrastructure.db.mappers import user_to_entity
from app.infrastructure.db.models import UserModel


class SqlUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, user: User) -> User:
        row = UserModel(
            email=user.email,
            full_name=user.full_name,
            password_hash=user.password_hash,
            created_at=user.created_at,
        )
        self._session.add(row)
        self._session.flush()
        return user_to_entity(row)

    def get(self, user_id: int) -> User | None:
        row = self._session.get(UserModel, user_id)
        return user_to_entity(row) if row else None

    def get_by_email(self, email: str) -> User | None:
        row = self._session.scalar(select(UserModel).where(UserModel.email == email))
        return user_to_entity(row) if row else None

    def list_all(self) -> list[User]:
        return [
            user_to_entity(r)
            for r in self._session.scalars(select(UserModel).order_by(UserModel.id))
        ]
