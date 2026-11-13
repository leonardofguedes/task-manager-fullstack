from datetime import UTC, datetime

import pytest

from app.application.auth_service import AuthService
from app.domain.errors import AuthenticationError, ConflictError, ValidationError
from tests.fakes import (
    FakeClock,
    FakeTokenService,
    FakeUnitOfWork,
    InMemoryUserRepository,
    PlainHasher,
)

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)


@pytest.fixture
def users() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def service(users: InMemoryUserRepository) -> AuthService:
    return AuthService(users, FakeUnitOfWork(), PlainHasher(), FakeTokenService(), FakeClock(NOW))


def test_register_normalizes_email_and_hashes_password(service: AuthService) -> None:
    user = service.register("  Alice@Example.COM ", "s3cret-pass", "Alice")

    assert user.id is not None
    assert user.email == "alice@example.com"
    assert user.password_hash == "hashed:s3cret-pass"


def test_register_duplicate_conflict(service: AuthService) -> None:
    service.register("alice@example.com", "s3cret-pass", "Alice")

    with pytest.raises(ConflictError):
        service.register("ALICE@example.com", "another-pass", "Alice 2")


def test_register_short_password(service: AuthService) -> None:
    with pytest.raises(ValidationError):
        service.register("alice@example.com", "short", "Alice")


def test_register_blank_name(service: AuthService) -> None:
    with pytest.raises(ValidationError):
        service.register("alice@example.com", "s3cret-pass", "   ")


def test_login_wrong_password_and_unknown_email_same_error(service: AuthService) -> None:
    service.register("alice@example.com", "s3cret-pass", "Alice")

    with pytest.raises(AuthenticationError) as wrong_password:
        service.login("alice@example.com", "nope-nope")
    with pytest.raises(AuthenticationError) as unknown_email:
        service.login("ghost@example.com", "s3cret-pass")

    assert str(wrong_password.value) == str(unknown_email.value) == "invalid credentials"


def test_login_returns_token_resolving_to_user(service: AuthService) -> None:
    user = service.register("alice@example.com", "s3cret-pass", "Alice")

    token = service.login(" ALICE@example.com", "s3cret-pass")

    assert service.resolve_user(token).id == user.id


def test_resolve_token_of_deleted_user_raises(
    service: AuthService, users: InMemoryUserRepository
) -> None:
    user = service.register("alice@example.com", "s3cret-pass", "Alice")
    token = service.login("alice@example.com", "s3cret-pass")
    del users.rows[user.id]  # type: ignore[arg-type]

    with pytest.raises(AuthenticationError):
        service.resolve_user(token)


def test_login_unknown_email_still_runs_one_password_check(users: InMemoryUserRepository) -> None:
    # Skipping the hash check for unknown emails would make them answer faster (enumeration).
    hasher = PlainHasher()
    service = AuthService(users, FakeUnitOfWork(), hasher, FakeTokenService(), FakeClock(NOW))

    with pytest.raises(AuthenticationError):
        service.login("nobody@example.com", "whatever-pass")

    assert hasher.checks == 1
