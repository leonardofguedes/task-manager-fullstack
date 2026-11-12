from collections.abc import Callable, Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import deps
from app.api.main import create_app
from app.config import Settings
from app.infrastructure.db.base import Base
from tests.fakes import RecordingDispatcher

TEST_SECRET = "integration-test-secret-" + "x" * 32
PASSWORD = "s3cret-pass"

AuthHeaders = Callable[..., dict[str, str]]


@pytest.fixture
def engine() -> Iterator[Engine]:
    # One shared in-memory connection so every session sees the same database.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as session:
        yield session


@pytest.fixture
def settings() -> Settings:
    return Settings(jwt_secret=TEST_SECRET, rate_limit_enabled=False)


@pytest.fixture
def dispatcher() -> RecordingDispatcher:
    return RecordingDispatcher()


@pytest.fixture
def app(
    settings: Settings, session_factory: sessionmaker[Session], dispatcher: RecordingDispatcher
) -> FastAPI:
    app = create_app(settings, session_factory=session_factory)
    app.dependency_overrides[deps.get_dispatcher] = lambda: dispatcher
    return app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


def register(client: TestClient, email: str, full_name: str | None = None) -> dict[str, object]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": full_name or email.split("@")[0]},
    )
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


def login(client: TestClient, email: str, password: str = PASSWORD) -> str:
    response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200, response.text
    token: str = response.json()["access_token"]
    return token


@pytest.fixture
def auth_headers(client: TestClient) -> AuthHeaders:
    """Register (once) and log in a user, returning its Authorization header."""
    registered: set[str] = set()

    def _headers(email: str = "alice@example.com") -> dict[str, str]:
        if email not in registered:
            register(client, email)
            registered.add(email)
        return {"Authorization": f"Bearer {login(client, email)}"}

    return _headers
