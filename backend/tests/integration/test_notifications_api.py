import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.worker import jobs
from tests.fakes import RecordingDispatcher
from tests.integration.conftest import AuthHeaders

NOTIFICATIONS = "/api/v1/notifications"


@pytest.fixture(autouse=True)
def jobs_use_test_db(
    monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]
) -> None:
    monkeypatch.setattr(jobs, "get_session_factory", lambda: session_factory)


def me(client: TestClient, headers: dict[str, str]) -> int:
    user_id: int = client.get("/api/v1/users/me", headers=headers).json()["id"]
    return user_id


def test_assign_then_job_creates_notification_for_assignee_only(
    client: TestClient, auth_headers: AuthHeaders, dispatcher: RecordingDispatcher
) -> None:
    alice, bob = auth_headers("alice@example.com"), auth_headers("bob@example.com")
    task = client.post(
        "/api/v1/tasks", json={"title": "Review PR", "assignee_id": me(client, bob)}, headers=alice
    ).json()

    # Run the job the dispatcher would have enqueued, exactly as the worker would.
    for task_id, assignee_id in dispatcher.calls:
        jobs.send_assignment_notification.run(task_id, assignee_id)

    bob_inbox = client.get(NOTIFICATIONS, headers=bob).json()
    assert [(n["task_id"], n["kind"], n["message"]) for n in bob_inbox] == [
        (task["id"], "assigned", 'You were assigned to "Review PR"')
    ]
    assert client.get(NOTIFICATIONS, headers=alice).json() == []


def test_scan_overdue_job_notifies_owner(client: TestClient, auth_headers: AuthHeaders) -> None:
    alice = auth_headers("alice@example.com")
    client.post("/api/v1/tasks", json={"title": "Old", "due_date": "2000-01-01"}, headers=alice)

    assert jobs.scan_overdue_tasks.run() == 1
    assert jobs.scan_overdue_tasks.run() == 0

    inbox = client.get(NOTIFICATIONS, headers=alice).json()
    assert [n["kind"] for n in inbox] == ["overdue"]


def test_notifications_limit_bounds(client: TestClient, auth_headers: AuthHeaders) -> None:
    alice = auth_headers("alice@example.com")

    assert client.get(NOTIFICATIONS, params={"limit": 101}, headers=alice).status_code == 422


def test_notifications_require_auth(client: TestClient) -> None:
    assert client.get(NOTIFICATIONS).status_code == 401
