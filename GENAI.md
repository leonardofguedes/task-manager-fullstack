# Generative AI: how it was used and validated

## Tool

**Claude Code** (Anthropic, Claude Opus model) running in my terminal and editor, with read and write access to the repository and permission to run commands (tests, linters, Docker). I treated it as a fast pair programmer: it proposed plans and code, and nothing was accepted without a failing test first, a green suite, and my own review of the diff.

## 1. The prompt

I did not ask for the whole application in one shot. One-shot generation produces plausible code that nobody has validated. The work ran in three stages: plan, implement task by task with TDD, then an independent review. The prompts below are the ones I recommend for each stage, cleaned up from the conversation that built this repo. My real requests were shorter and iterative, and the plan itself carried most of the detail.

### Stage 1: plan, before any code

```text
You are a senior Python engineer. Read the exercise below and produce an implementation plan,
not code. I will review the plan before anything is written.

<exercise text pasted here>

Constraints:
- FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL (SQLite for tests), JWT, Celery + Redis,
  React + TypeScript + Vite frontend, Docker Compose, uv + pre-commit.
- Clean Architecture: domain (pure Python) -> application (use cases + Protocol ports)
  -> infrastructure (adapters) / api (FastAPI). Imports only point inward.
- TDD: every task lists the failing tests first, with their names and exact assertions.

For each task give: files to create, exact function signatures and types that other tasks
depend on, the tests (names + assertions), the command to verify, and the commit message.
List the ambiguities in the exercise and propose a resolution for each. List the edge cases
the exercise does not mention but a real user would hit (inverted date ranges, unknown
assignee, pagination bounds, expired tokens, permission checks).
```

### Stage 2: scaffold and implement one task at a time (example: the task use cases)

```text
Implement Task 2 of the plan (task use cases) using TDD.

1. Write tests/unit/test_task_service.py with exactly the tests listed in the plan, using the
   in-memory fakes from tests/fakes.py. Run them and show me that they fail for the right
   reason (missing module), not a typo.
2. Implement app/application/ports.py and app/application/task_service.py with the
   signatures from the plan. Keep business rules in the domain entity, not in the service.
3. The NotificationDispatcher must be called only AFTER uow.commit(); add a test that proves
   the order.
4. Run the full suite, ruff and mypy --strict. Do not weaken a test to make it pass.
```

### Stage 3: adversarial review

```text
Review this branch as a strict senior reviewer who wants to reject it. Look for: broken
authorization paths, unvalidated input reaching the domain, error paths returning 500,
transaction/ordering bugs between the API and the worker, timezone bugs, N+1 queries,
anything in the README that the code does not actually do. For each finding give the
input that triggers it and the expected behaviour.
```

## 2. Representative output

The assignment rule as generated, after review. Note the comment explaining the ordering:

```python
# app/application/task_service.py
def update(self, actor_id: int, task_id: int, changes: TaskChanges) -> Task:
    task = self._load(task_id)
    if not task.can_edit(actor_id):
        raise PermissionDeniedError("only the owner or the assignee can edit this task")
    previous_assignee = task.assignee_id
    now = self._clock.now()
    ...
    if "assignee_id" in changes:
        self._ensure_assignee_exists(changes["assignee_id"])
        task.assign(changes["assignee_id"], now)

    saved = self._tasks.update(task)
    self._uow.commit()
    self._notify_if_newly_assigned(saved, previous_assignee, actor_id)
    return saved

def _notify_if_newly_assigned(self, task, previous_assignee, actor_id) -> None:
    # Called only after commit, so the worker never races an uncommitted row.
    assignee = task.assignee_id
    if assignee is None or assignee in (previous_assignee, actor_id):
        return
    self._dispatcher.task_assigned(task.id, assignee)
```

And the test that pins the behaviour, written before the implementation:

```python
def test_create_with_assignee_dispatches_after_commit(service, dispatcher) -> None:
    task = service.create(ALICE, TaskCreate(title="x", assignee_id=BOB))

    assert dispatcher.calls == [(task.id, BOB)]
    assert dispatcher.commits_at_call == [1]  # the commit had already happened
```

## 3. How I validated the AI's suggestions

1. **Tests first, always.** Every behaviour got a failing test before the code existed, and I checked that it failed *for the right reason*. A test that passes before the implementation is a finding about the test.
2. **Read every diff.** Generated code that "looks right" is the most dangerous kind. I read each change for intent, not just syntax.
3. **Automated gates on every commit.** ruff (lint + format), mypy in strict mode, oxlint, and the 80% coverage gate. Several real bugs below were caught here, not by eye.
4. **Run the real system.** After the backend was done, I ran the full Docker stack and drove it end to end: API calls, worker logs, then the browser at desktop and phone widths with the console open. Unit tests cannot catch scheduling or proxy issues.
5. **Keep a correction log.** Each time I had to change generated code, I wrote down what and why. That log is the table below.

## 4. What I corrected or improved

| # | What the AI produced or missed | Why it was wrong | Fix |
|---|---|---|---|
| 1 | Domain compared status with `is TaskStatus.DONE` | A repository test passed `"done"` as a plain string: it was stored, but `completed_at` was silently never set | The domain now coerces and validates status (`ValidationError` for unknown values). Tests first. |
| 2 | Timestamps round-tripped through SQLite came back *naive* | SQLite drops timezone info, so comparisons with aware datetimes would break or shift | `UTCDateTime` column type (aware in, aware out). The round-trip test asserts `tzinfo`. |
| 3 | The plan said slowapi for rate limiting | Its decorators bind the limiter config at import time, which conflicts with the app factory and per-test settings | A small FastAPI dependency on `limits` (slowapi's own engine), configured per app instance. |
| 4 | Celery Beat with a 15-minute interval | In the live run, nothing happened at start-up: interval jobs first fire after one full interval, so the demo showed no overdue notifications | A `beat_init` hook runs one scan on start (safe because the scan is idempotent). |
| 5 | Alembic autogenerate imported `app...UTCDateTime` into the migration | Migration history must not depend on application code that can change later | Replaced with `sa.DateTime(timezone=True)`, then verified with upgrade, downgrade and `alembic check`. |
| 6 | Short JWT secrets in tests | PyJWT warned that HMAC keys under 32 bytes are insecure (RFC 7518) | `Settings.jwt_secret` now requires ≥ 32 characters, so the app refuses to start with a weak secret. |
| 7 | A repository method named `list` and the annotation `-> list[Task]` in the same class | The method shadows the builtin: `TypeError` at import, and mypy rejects it as a type | Postponed annotations plus `builtins.list[Task]`. |
| 8 | Circular import between `ports.py` and `task_service.py` | Ports needed `TaskFilters`, and the service needs the ports | A `TYPE_CHECKING`-only import (types only, no runtime cycle). |
| 9 | CI step `DATABASE_URL=... alembic upgrade && alembic check` | The env var applied to the first command only, so the check ran against a different database | A step-level `env:` block. |
| 10 | Line endings on Windows | Git would have committed CRLF, which breaks shell scripts inside Linux containers | `.gitattributes` with `eol=lf`. |
| 11 | Test client used the deprecated `httpx` path | Warnings in the test output hide real ones | Switched to `httpx2`; the suite runs with zero warnings. |
| 12 | Leftovers from scaffolding (`hello-world` entry point, template assets) | Dead code | Removed. |

## 5. Edge cases, authentication and validation

- **Validation in two places:** Pydantic for shape and types at the edge (422), and the domain for invariants such as a non-blank title, length limits and valid status. The domain never trusts the edge.
- **Authorization lives in the domain** (`can_edit`, `can_delete`) and is enforced by the use case. The UI only hides buttons as a convenience; the API returns 403 regardless.
- **Explicit edge-case tests:** inverted date range (422, not an empty list), inclusive range boundaries, unknown assignee (422, not 500), `limit` outside 1–100 (422), `offset` past the end (empty `items` with the correct `total`), `PATCH` with `null` versus an omitted field, `null` title (422), unknown task (404).
- **Authentication edge cases:** expired, malformed, wrong-secret, tampered, `alg: none`, non-integer `sub`, and the token of a deleted user. All return 401 with `WWW-Authenticate: Bearer`, never 500. Login gives the same message for an unknown email and a wrong password.
- **Worker edge cases:** a job for a task that was deleted or reassigned in the meantime does nothing; the overdue scan is idempotent; jobs receive ids rather than serialised objects, so they always read fresh data.

## 6. Performance and idiomatic quality

- **Queries:** list endpoints run one `COUNT` plus one page query, with no N+1 (no lazy relationships are traversed). Indexes on `(status, due_date)`, `due_date`, `assignee_id`, `owner_id` and `users.email` match the filters and joins.
- **Ordering is deterministic** (`due_date` with nulls last, then `id`), so pagination is stable. Keyset pagination would be the next step for very large tables.
- **Sync over async** was a deliberate choice for this workload (see PRESENTATION.md). It is isolated behind the repository ports.
- **Idiomatic Python:** dataclasses for entities, `StrEnum` for statuses, `Protocol` for ports, `Annotated` dependencies in FastAPI, SQLAlchemy 2.0 typed `Mapped[...]` models, and `mypy --strict` clean.
- **Frontend:** TanStack Query with `keepPreviousData` (no flicker while paging), the native `<dialog>` element (focus trap and Esc for free), and touch targets of at least 44 px. A production build has zero console warnings.

## 7. Takeaways

The AI was fastest at boilerplate (schemas, routers, mappers, Docker files) and at producing a coherent plan. It was weakest exactly where software usually breaks: types crossing boundaries (strings versus enums, naive versus aware datetimes), framework lifecycle details (decorator binding time, scheduler first run) and shell semantics. Tests written first, strict static checks, and running the real system caught all of them. That is the workflow I would keep.
