"""Idempotent demo data: `python -m app.seed`. Goes through the real use cases."""

import logging
from datetime import timedelta

from sqlalchemy.orm import Session, sessionmaker

from app.application.auth_service import AuthService
from app.application.ports import Clock, PasswordHasher
from app.application.task_service import TaskCreate, TaskService
from app.domain.ids import persisted_id
from app.domain.tasks import TaskStatus
from app.infrastructure.repositories.tasks import SqlTaskRepository
from app.infrastructure.repositories.uow import SqlUnitOfWork
from app.infrastructure.repositories.users import SqlUserRepository

logger = logging.getLogger(__name__)

DEMO_PASSWORD = "demo1234"  # documented demo credential, not a secret


class _NoDispatch:
    """Seeding must not flood the queue with assignment notifications."""

    def task_assigned(self, task_id: int, assignee_id: int) -> None:
        return None


class _NoTokens:
    def issue(self, user_id: int) -> str:
        raise NotImplementedError

    def decode(self, token: str) -> int:
        raise NotImplementedError


def seed(session_factory: sessionmaker[Session], hasher: PasswordHasher, clock: Clock) -> bool:
    """Create demo users and tasks. Returns False when the data already exists."""
    with session_factory() as session:
        users = SqlUserRepository(session)
        if users.get_by_email("alice@example.com") is not None:
            return False
        uow = SqlUnitOfWork(session)
        auth = AuthService(users, uow, hasher, _NoTokens(), clock)
        alice = auth.register("alice@example.com", DEMO_PASSWORD, "Alice Martins")
        bob = auth.register("bob@example.com", DEMO_PASSWORD, "Bob Silva")
        alice_id, bob_id = persisted_id(alice.id), persisted_id(bob.id)

        tasks = TaskService(SqlTaskRepository(session), users, uow, _NoDispatch(), clock)
        today = clock.today()
        demo: list[tuple[int, str, TaskStatus, int | None, int | None]] = [
            (alice_id, "Set up CI pipeline", TaskStatus.DONE, -6, bob_id),
            (alice_id, "Write API documentation", TaskStatus.IN_PROGRESS, 2, None),
            (alice_id, "Review pull request #42", TaskStatus.TODO, -2, bob_id),
            (alice_id, "Plan next sprint", TaskStatus.TODO, 5, None),
            (alice_id, "Fix login rate limit bug", TaskStatus.TODO, -1, None),
            (alice_id, "Prepare demo for stakeholders", TaskStatus.TODO, 10, bob_id),
            (bob_id, "Design database indexes", TaskStatus.DONE, -3, None),
            (bob_id, "Add pagination to task list", TaskStatus.IN_PROGRESS, 1, alice_id),
            (bob_id, "Update dependencies", TaskStatus.TODO, 14, None),
            (bob_id, "Investigate slow query", TaskStatus.TODO, -4, alice_id),
            (bob_id, "Write onboarding guide", TaskStatus.TODO, None, None),
            (bob_id, "Refactor notification worker", TaskStatus.IN_PROGRESS, 7, None),
        ]
        for owner, title, status, due_in, assignee in demo:
            tasks.create(
                owner,
                TaskCreate(
                    title=title,
                    status=status,
                    due_date=None if due_in is None else today + timedelta(days=due_in),
                    assignee_id=assignee,
                    description=f"Demo task: {title.lower()}.",
                ),
            )
        return True


def main() -> None:
    from app.config import get_infra_settings
    from app.infrastructure.clock import SystemClock
    from app.infrastructure.db.session import make_engine, make_session_factory
    from app.infrastructure.security.hashing import Argon2Hasher

    logging.basicConfig(level=logging.INFO)
    factory = make_session_factory(make_engine(get_infra_settings().database_url))
    created = seed(factory, Argon2Hasher(), SystemClock())
    logger.info("seed: %s", "demo data created" if created else "already seeded, skipping")


if __name__ == "__main__":
    main()
