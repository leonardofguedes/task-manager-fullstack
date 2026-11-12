from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.infrastructure.db.models import UserModel
from app.infrastructure.security.jwt_tokens import JwtTokenService
from tests.fakes import FakeClock
from tests.integration.conftest import TEST_SECRET, AuthHeaders, login, register


def test_register_201_and_password_not_returned(client: TestClient) -> None:
    body = register(client, "Alice@Example.com", "Alice")

    assert body["email"] == "alice@example.com"
    assert body["full_name"] == "Alice"
    assert "password" not in body and "password_hash" not in body


def test_register_duplicate_409(client: TestClient) -> None:
    register(client, "alice@example.com")

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "ALICE@example.com", "password": "another-pass", "full_name": "A"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "email already registered"}


def test_register_invalid_email_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "s3cret-pass", "full_name": "A"},
    )

    assert response.status_code == 422


def test_register_short_password_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "a@example.com", "password": "short", "full_name": "A"},
    )

    assert response.status_code == 422


def test_login_200_returns_bearer(client: TestClient) -> None:
    register(client, "alice@example.com")

    response = client.post(
        "/api/v1/auth/login", data={"username": "alice@example.com", "password": "s3cret-pass"}
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_wrong_password_401(client: TestClient) -> None:
    register(client, "alice@example.com")

    response = client.post(
        "/api/v1/auth/login", data={"username": "alice@example.com", "password": "wrong-pass"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid credentials"}


def test_me_requires_token_401_with_www_authenticate(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_with_malformed_token_401(client: TestClient) -> None:
    response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer not.a.jwt"})

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_with_expired_token_401(client: TestClient) -> None:
    user = register(client, "alice@example.com")
    issued_long_ago = FakeClock(datetime.now(UTC) - timedelta(hours=2))
    token = JwtTokenService(TEST_SECRET, "HS256", 60, issued_long_ago).issue(int(user["id"]))  # type: ignore[call-overload]

    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_me_after_user_deleted_401(client: TestClient, session: Session) -> None:
    user = register(client, "alice@example.com")
    token = login(client, "alice@example.com")
    session.delete(session.get_one(UserModel, user["id"]))
    session.commit()

    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_me_returns_current_user(client: TestClient, auth_headers: AuthHeaders) -> None:
    response = client.get("/api/v1/users/me", headers=auth_headers("alice@example.com"))

    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"


def test_list_users(client: TestClient, auth_headers: AuthHeaders) -> None:
    auth_headers("bob@example.com")

    response = client.get("/api/v1/users", headers=auth_headers("alice@example.com"))

    assert response.status_code == 200
    assert [u["email"] for u in response.json()] == ["bob@example.com", "alice@example.com"]
