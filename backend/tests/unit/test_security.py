from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.domain.errors import AuthenticationError
from app.infrastructure.security.hashing import Argon2Hasher
from app.infrastructure.security.jwt_tokens import JwtTokenService
from tests.fakes import FakeClock

TEST_SECRET = "test-secret-" + "x" * 32
NOW = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)


def make_service(clock: FakeClock, secret: str = TEST_SECRET) -> JwtTokenService:
    return JwtTokenService(secret=secret, algorithm="HS256", expire_minutes=60, clock=clock)


def test_argon2_roundtrip() -> None:
    hasher = Argon2Hasher()

    hashed = hasher.hash("s3cret-pass")

    assert hashed != "s3cret-pass"
    assert hashed.startswith("$argon2id$")
    assert hasher.verify("s3cret-pass", hashed)
    assert not hasher.verify("wrong", hashed)


def test_jwt_roundtrip() -> None:
    service = make_service(FakeClock(datetime.now(UTC)))

    assert service.decode(service.issue(42)) == 42


def test_jwt_expired_raises() -> None:
    issuer = make_service(FakeClock(datetime.now(UTC) - timedelta(minutes=61)))
    token = issuer.issue(42)

    with pytest.raises(AuthenticationError):
        make_service(FakeClock(datetime.now(UTC))).decode(token)


def test_jwt_tampered_raises() -> None:
    service = make_service(FakeClock(datetime.now(UTC)))
    header, payload, signature = service.issue(42).split(".")

    with pytest.raises(AuthenticationError):
        service.decode(f"{header}.{payload}.{signature[::-1]}")


def test_jwt_wrong_secret_raises() -> None:
    token = make_service(FakeClock(datetime.now(UTC)), secret="o" * 32).issue(42)

    with pytest.raises(AuthenticationError):
        make_service(FakeClock(datetime.now(UTC))).decode(token)


def test_jwt_non_integer_subject_raises() -> None:
    token = jwt.encode(
        {"sub": "admin", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(AuthenticationError):
        make_service(FakeClock(NOW)).decode(token)


def test_jwt_rejects_none_algorithm() -> None:
    token = jwt.encode({"sub": "42"}, None, algorithm="none")

    with pytest.raises(AuthenticationError):
        make_service(FakeClock(NOW)).decode(token)
