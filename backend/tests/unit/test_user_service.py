from datetime import UTC, datetime

from app.application.user_service import UserService
from app.domain.users import User
from tests.fakes import InMemoryUserRepository

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)


def test_list_all_returns_every_user() -> None:
    users = InMemoryUserRepository()
    alice = users.add(User(None, "alice@example.com", "Alice", "h", NOW))
    bob = users.add(User(None, "bob@example.com", "Bob", "h", NOW))

    assert UserService(users).list_all() == [alice, bob]
