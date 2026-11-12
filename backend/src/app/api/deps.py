"""Composition root: wires adapters into use cases for each request via FastAPI `Depends`."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.application.auth_service import AuthService
from app.application.ports import Clock, NotificationDispatcher
from app.application.task_service import TaskService
from app.config import Settings
from app.domain.users import User
from app.infrastructure.clock import SystemClock
from app.infrastructure.repositories.tasks import SqlTaskRepository
from app.infrastructure.repositories.uow import SqlUnitOfWork
from app.infrastructure.repositories.users import SqlUserRepository
from app.infrastructure.security.hashing import Argon2Hasher
from app.infrastructure.security.jwt_tokens import JwtTokenService
from app.infrastructure.worker.dispatcher import CeleryNotificationDispatcher

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
_hasher = Argon2Hasher()


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_session(request: Request) -> Iterator[Session]:
    session: Session = request.app.state.session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_clock() -> Clock:
    return SystemClock()


def get_dispatcher() -> NotificationDispatcher:
    return CeleryNotificationDispatcher()


SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]


def get_auth_service(settings: SettingsDep, session: SessionDep, clock: ClockDep) -> AuthService:
    tokens = JwtTokenService(
        settings.jwt_secret, settings.jwt_algorithm, settings.access_token_expire_minutes, clock
    )
    return AuthService(SqlUserRepository(session), SqlUnitOfWork(session), _hasher, tokens, clock)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], auth: AuthServiceDep) -> User:
    return auth.resolve_user(token)


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_task_service(
    session: SessionDep,
    clock: ClockDep,
    dispatcher: Annotated[NotificationDispatcher, Depends(get_dispatcher)],
) -> TaskService:
    return TaskService(
        SqlTaskRepository(session),
        SqlUserRepository(session),
        SqlUnitOfWork(session),
        dispatcher,
        clock,
    )


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
