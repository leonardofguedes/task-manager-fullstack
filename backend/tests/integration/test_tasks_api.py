from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.fakes import RecordingDispatcher
from tests.integration.conftest import AuthHeaders

TASKS = "/api/v1/tasks"


@pytest.fixture
def alice(auth_headers: AuthHeaders) -> dict[str, str]:
    return auth_headers("alice@example.com")


@pytest.fixture
def bob(auth_headers: AuthHeaders) -> dict[str, str]:
    return auth_headers("bob@example.com")


@pytest.fixture
def carol(auth_headers: AuthHeaders) -> dict[str, str]:
    return auth_headers("carol@example.com")


def user_id(client: TestClient, headers: dict[str, str]) -> int:
    user_id: int = client.get("/api/v1/users/me", headers=headers).json()["id"]
    return user_id


def create(client: TestClient, headers: dict[str, str], **fields: Any) -> dict[str, Any]:
    response = client.post(TASKS, json={"title": "Task", **fields}, headers=headers)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def titles(response: Any) -> list[str]:
    return [t["title"] for t in response.json()["items"]]


def test_crud_happy_path(client: TestClient, alice: dict[str, str]) -> None:
    created = create(
        client, alice, title="Write README", description="setup", due_date="2026-12-01"
    )
    task_url = f"{TASKS}/{created['id']}"
    assert created["status"] == "todo"
    assert created["owner_id"] == user_id(client, alice)

    assert client.get(task_url, headers=alice).json()["title"] == "Write README"

    patched = client.patch(task_url, json={"title": "Write docs"}, headers=alice)
    assert patched.status_code == 200
    assert patched.json()["title"] == "Write docs"
    assert patched.json()["description"] == "setup"

    assert client.delete(task_url, headers=alice).status_code == 204
    assert client.get(task_url, headers=alice).status_code == 404


def test_list_requires_auth(client: TestClient) -> None:
    assert client.get(TASKS).status_code == 401


def test_create_blank_title_422(client: TestClient, alice: dict[str, str]) -> None:
    response = client.post(TASKS, json={"title": "   "}, headers=alice)

    assert response.status_code == 422


def test_filter_by_status(client: TestClient, alice: dict[str, str]) -> None:
    create(client, alice, title="open")
    create(client, alice, title="finished", status="done")

    response = client.get(TASKS, params={"status": "done"}, headers=alice)

    assert titles(response) == ["finished"]


def test_filter_by_invalid_status_422(client: TestClient, alice: dict[str, str]) -> None:
    assert client.get(TASKS, params={"status": "archived"}, headers=alice).status_code == 422


def test_filter_by_due_range_inclusive(client: TestClient, alice: dict[str, str]) -> None:
    for day in ("10", "15", "20", "25"):
        create(client, alice, title=f"due {day}", due_date=f"2026-11-{day}")

    response = client.get(
        TASKS, params={"due_after": "2026-11-15", "due_before": "2026-11-20"}, headers=alice
    )

    assert titles(response) == ["due 15", "due 20"]


def test_inverted_due_range_422(client: TestClient, alice: dict[str, str]) -> None:
    response = client.get(
        TASKS, params={"due_after": "2026-11-20", "due_before": "2026-11-10"}, headers=alice
    )

    assert response.status_code == 422
    assert "due_after" in response.json()["detail"]


@pytest.mark.parametrize("limit", [0, 101])
def test_limit_bounds_422(client: TestClient, alice: dict[str, str], limit: int) -> None:
    assert client.get(TASKS, params={"limit": limit}, headers=alice).status_code == 422


def test_negative_offset_422(client: TestClient, alice: dict[str, str]) -> None:
    assert client.get(TASKS, params={"offset": -1}, headers=alice).status_code == 422


def test_pagination_and_offset_past_end(client: TestClient, alice: dict[str, str]) -> None:
    for i in range(5):
        create(client, alice, title=f"t{i}")

    page = client.get(TASKS, params={"limit": 2, "offset": 2}, headers=alice).json()
    past_end = client.get(TASKS, params={"limit": 2, "offset": 50}, headers=alice).json()

    assert (len(page["items"]), page["total"], page["limit"], page["offset"]) == (2, 5, 2, 2)
    assert past_end["items"] == [] and past_end["total"] == 5


def test_assign_unknown_user_422(client: TestClient, alice: dict[str, str]) -> None:
    response = client.post(TASKS, json={"title": "x", "assignee_id": 999}, headers=alice)

    assert response.status_code == 422
    assert response.json() == {"detail": "assignee not found"}


def test_assign_dispatches_notification(
    client: TestClient,
    alice: dict[str, str],
    bob: dict[str, str],
    dispatcher: RecordingDispatcher,
) -> None:
    bob_id = user_id(client, bob)
    task = create(client, alice)

    client.patch(f"{TASKS}/{task['id']}", json={"assignee_id": bob_id}, headers=alice)

    assert dispatcher.calls == [(task["id"], bob_id)]


def test_filter_by_assignee(client: TestClient, alice: dict[str, str], bob: dict[str, str]) -> None:
    create(client, alice, title="mine")
    create(client, alice, title="for bob", assignee_id=user_id(client, bob))

    response = client.get(TASKS, params={"assignee_id": user_id(client, bob)}, headers=alice)

    assert titles(response) == ["for bob"]


def test_patch_by_stranger_403(
    client: TestClient, alice: dict[str, str], carol: dict[str, str]
) -> None:
    task = create(client, alice)

    response = client.patch(f"{TASKS}/{task['id']}", json={"title": "mine now"}, headers=carol)

    assert response.status_code == 403


def test_assignee_can_patch_but_not_delete(
    client: TestClient, alice: dict[str, str], bob: dict[str, str]
) -> None:
    task = create(client, alice, assignee_id=user_id(client, bob))
    url = f"{TASKS}/{task['id']}"

    assert client.patch(url, json={"status": "in_progress"}, headers=bob).status_code == 200
    assert client.delete(url, headers=bob).status_code == 403


def test_patch_null_clears_due_date_and_absent_field_is_kept(
    client: TestClient, alice: dict[str, str]
) -> None:
    task = create(client, alice, description="keep me", due_date="2026-12-01")

    body = client.patch(f"{TASKS}/{task['id']}", json={"due_date": None}, headers=alice).json()

    assert body["due_date"] is None
    assert body["description"] == "keep me"


def test_patch_null_title_422(client: TestClient, alice: dict[str, str]) -> None:
    task = create(client, alice)

    response = client.patch(f"{TASKS}/{task['id']}", json={"title": None}, headers=alice)

    assert response.status_code == 422


def test_get_unknown_404(client: TestClient, alice: dict[str, str]) -> None:
    response = client.get(f"{TASKS}/12345", headers=alice)

    assert response.status_code == 404
    assert response.json() == {"detail": "task 12345 not found"}


def test_complete_sets_completed_at(client: TestClient, alice: dict[str, str]) -> None:
    task = create(client, alice)

    body = client.post(f"{TASKS}/{task['id']}/complete", headers=alice).json()

    assert body["status"] == "done"
    assert body["completed_at"] is not None


def test_is_overdue_flag(client: TestClient, alice: dict[str, str]) -> None:
    late = create(client, alice, due_date="2000-01-01")
    future = create(client, alice, due_date="2999-01-01")

    assert late["is_overdue"] is True
    assert future["is_overdue"] is False


INT32_OVERFLOW = 2**31  # first value Postgres INTEGER cannot hold
INT64_OVERFLOW = 2**63


@pytest.mark.parametrize("bad_id", [0, INT32_OVERFLOW, INT64_OVERFLOW])
def test_out_of_range_task_id_is_422_not_500(
    client: TestClient, alice: dict[str, str], bad_id: int
) -> None:
    assert client.get(f"{TASKS}/{bad_id}", headers=alice).status_code == 422
    assert client.delete(f"{TASKS}/{bad_id}", headers=alice).status_code == 422
    assert client.post(f"{TASKS}/{bad_id}/complete", headers=alice).status_code == 422
    patch = client.patch(f"{TASKS}/{bad_id}", json={"title": "x"}, headers=alice)
    assert patch.status_code == 422


@pytest.mark.parametrize("bad_id", [0, INT32_OVERFLOW, INT64_OVERFLOW])
def test_out_of_range_assignee_is_422_not_500(
    client: TestClient, alice: dict[str, str], bad_id: int
) -> None:
    task = create(client, alice)

    created = client.post(TASKS, json={"title": "x", "assignee_id": bad_id}, headers=alice)
    patched = client.patch(f"{TASKS}/{task['id']}", json={"assignee_id": bad_id}, headers=alice)
    listed = client.get(TASKS, params={"assignee_id": bad_id}, headers=alice)

    assert (created.status_code, patched.status_code, listed.status_code) == (422, 422, 422)


def test_huge_offset_is_422_not_500(client: TestClient, alice: dict[str, str]) -> None:
    assert client.get(TASKS, params={"offset": INT64_OVERFLOW}, headers=alice).status_code == 422
