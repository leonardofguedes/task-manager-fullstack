import pytest
from pydantic import ValidationError

from app.config import Settings


def test_short_jwt_secret_rejected() -> None:
    with pytest.raises(ValidationError, match="at least 32"):
        Settings(jwt_secret="too-short")


def test_long_jwt_secret_accepted() -> None:
    assert Settings(jwt_secret="x" * 32).jwt_secret == "x" * 32
