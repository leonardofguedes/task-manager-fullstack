from datetime import date
from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status

from app.api.deps import ClockDep, CurrentUser, TaskServiceDep
from app.api.schemas import TaskIn, TaskOut, TaskPage, TaskPatch
from app.application.pagination import PageParams
from app.application.task_service import TaskChanges, TaskCreate, TaskFilters
from app.domain.ids import MAX_ID, MIN_ID
from app.domain.tasks import TaskStatus

TaskId = Annotated[int, Path(ge=MIN_ID, le=MAX_ID)]

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("")
def list_tasks(
    user: CurrentUser,
    service: TaskServiceDep,
    clock: ClockDep,
    status_: Annotated[TaskStatus | None, Query(alias="status")] = None,
    due_after: Annotated[date | None, Query(description="Inclusive lower bound")] = None,
    due_before: Annotated[date | None, Query(description="Inclusive upper bound")] = None,
    assignee_id: Annotated[int | None, Query(ge=MIN_ID, le=MAX_ID)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=MAX_ID)] = 0,
) -> TaskPage:
    """List tasks ordered by due date (tasks without a due date last)."""
    assert user.id is not None
    page = service.list(
        user.id,
        TaskFilters(
            status=status_, due_after=due_after, due_before=due_before, assignee_id=assignee_id
        ),
        PageParams(limit=limit, offset=offset),
    )
    today = clock.today()
    return TaskPage(
        items=[TaskOut.from_entity(t, today) for t in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskIn, user: CurrentUser, service: TaskServiceDep, clock: ClockDep
) -> TaskOut:
    assert user.id is not None
    task = service.create(user.id, TaskCreate(**payload.model_dump()))
    return TaskOut.from_entity(task, clock.today())


@router.get("/{task_id}")
def get_task(
    task_id: TaskId, user: CurrentUser, service: TaskServiceDep, clock: ClockDep
) -> TaskOut:
    assert user.id is not None
    return TaskOut.from_entity(service.get(user.id, task_id), clock.today())


@router.patch("/{task_id}")
def update_task(
    task_id: TaskId, payload: TaskPatch, user: CurrentUser, service: TaskServiceDep, clock: ClockDep
) -> TaskOut:
    """Owner or assignee only. Omitted fields are kept; `null` clears a nullable field."""
    assert user.id is not None
    changes: TaskChanges = payload.model_dump(exclude_unset=True)  # type: ignore[assignment]
    return TaskOut.from_entity(service.update(user.id, task_id, changes), clock.today())


@router.post("/{task_id}/complete")
def complete_task(
    task_id: TaskId, user: CurrentUser, service: TaskServiceDep, clock: ClockDep
) -> TaskOut:
    assert user.id is not None
    return TaskOut.from_entity(service.complete(user.id, task_id), clock.today())


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: TaskId, user: CurrentUser, service: TaskServiceDep) -> Response:
    """Owner only."""
    assert user.id is not None
    service.delete(user.id, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
