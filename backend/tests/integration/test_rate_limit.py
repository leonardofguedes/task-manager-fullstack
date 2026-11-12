from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.main import create_app
from app.config import Settings
from tests.integration.conftest import TEST_SECRET


@pytest.fixture
def limited_client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    settings = Settings(
        jwt_secret=TEST_SECRET,
        rate_limit_enabled=True,
        rate_limit_default="8/minute",
        rate_limit_login="5/minute",
        rate_limit_storage_uri="memory://",
    )
    with TestClient(create_app(settings, session_factory=session_factory)) as client:
        yield client


def bad_login(client: TestClient) -> int:
    response = client.post(
        "/api/v1/auth/login", data={"username": "x@example.com", "password": "wrong-pass"}
    )
    return response.status_code


def test_login_rate_limited_after_5_attempts(limited_client: TestClient) -> None:
    assert [bad_login(limited_client) for _ in range(5)] == [401] * 5

    response = limited_client.post(
        "/api/v1/auth/login", data={"username": "x@example.com", "password": "wrong-pass"}
    )

    assert response.status_code == 429
    assert response.json() == {"detail": "rate limit exceeded"}
    assert int(response.headers["Retry-After"]) > 0


def test_default_limit_applies_to_api_routes(limited_client: TestClient) -> None:
    statuses = [limited_client.get("/api/v1/tasks").status_code for _ in range(9)]

    assert statuses == [401] * 8 + [429]


def test_health_not_rate_limited(limited_client: TestClient) -> None:
    statuses = {limited_client.get("/health").status_code for _ in range(20)}

    assert statuses == {200}


def test_disabled_limiter_never_blocks(client: TestClient) -> None:
    assert {bad_login(client) for _ in range(10)} == {401}


def test_register_uses_strict_limit(limited_client: TestClient) -> None:
    statuses = [
        limited_client.post(
            "/api/v1/auth/register",
            json={"email": f"u{i}@example.com", "password": "s3cret-pass", "full_name": "U"},
        ).status_code
        for i in range(6)
    ]

    assert statuses == [201] * 5 + [429]
