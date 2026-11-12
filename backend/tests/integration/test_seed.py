from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import TaskModel, UserModel
from app.seed import DEMO_PASSWORD, seed
from tests.fakes import FakeClock, PlainHasher

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)


def count(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_seed_creates_demo_users_and_tasks_once(session_factory: sessionmaker[Session]) -> None:
    assert seed(session_factory, PlainHasher(), FakeClock(NOW)) is True
    assert seed(session_factory, PlainHasher(), FakeClock(NOW)) is False

    with session_factory() as session:
        emails = session.scalars(select(UserModel.email).order_by(UserModel.id)).all()
        assert emails == ["alice@example.com", "bob@example.com"]
        assert count(session, TaskModel) == 12
        statuses = set(session.scalars(select(TaskModel.status)))
        assert statuses == {"todo", "in_progress", "done"}
        overdue = session.scalar(
            select(func.count())
            .select_from(TaskModel)
            .where(TaskModel.due_date < NOW.date(), TaskModel.status != "done")
        )
        assert overdue and overdue >= 2
        alice = session.scalars(select(UserModel)).first()
        assert alice is not None and PlainHasher().verify(DEMO_PASSWORD, alice.password_hash)
