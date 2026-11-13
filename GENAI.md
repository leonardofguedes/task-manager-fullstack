# Generative AI: how it was used and validated

## Tool and division of work

I used **Claude Code** (Anthropic, Claude Opus model) in my terminal, with read/write access to the repository and permission to run tests, linters and Docker.

To be explicit about authorship:

- **The AI wrote most of the code, tests and documentation.**
- **I made the decisions:** stack, architecture, what the background jobs do, and permission rules.
- **I reviewed the diffs** and decided which findings to fix and which to defer.
- **Running things:** the AI ran the tests, the Docker stack and the browser checks in my terminal, and I checked the results.

The work ran in three stages:

1. **Plan.** A written plan with interfaces and tests per step, reviewed before any code existed.
2. **Implement.** The AI implemented the plan step by step with TDD in the session: tests first, run red, then code, then green.
3. **Review.** I ran two independent adversarial reviews with fresh AI agents that had not seen the conversation, and fixed what they found.

**About the git history.** Each commit holds a finished plan step with its tests, so the commit order does not show the red/green cycle; that happened inside the session. The two later rounds of fixes are in their own commits, and they show what the reviews found.

## 1. The prompts

I didn't generate the application in one shot. The prompts below are cleaned-up versions of the ones I used; my real messages were shorter and iterative, and the plan carried most of the detail.

**Plan.**

```text
Read the exercise below and produce an implementation plan, not code. I will review it first.
<exercise text>
Constraints: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL (SQLite in tests), JWT, Celery + Redis,
React + TypeScript + Vite, Docker Compose, uv + pre-commit. Clean Architecture with imports
pointing inward only. For each task: files, exact signatures other tasks depend on, the failing
tests to write first (names + assertions), the verify command. List the ambiguities in the
exercise with a proposed resolution, and the edge cases a real user would hit.
```

**Implementation, one task at a time.**

```text
Implement Task 2 (task use cases) with TDD. Write the listed tests against the in-memory fakes,
run them and show they fail for the right reason. Then implement the ports and the service.
The notification dispatcher must be called only after uow.commit(); add a test that proves the
order. Run the full suite, ruff and mypy --strict. Do not weaken a test to make it pass.
```

**Adversarial review**, given to a fresh agent with no access to our conversation.

```text
Review this branch as a strict senior reviewer who wants to reject it: broken authorization,
unvalidated input reaching the domain, error paths returning 500, ordering bugs between the API
and the worker, anything the README claims that the code doesn't do. For each finding give the
input that triggers it and the expected behaviour.
```

## 2. Representative output

The assignment notification, as generated and kept after review:

```python
# app/application/task_service.py
saved = self._tasks.update(task)
self._uow.commit()
self._notify_if_newly_assigned(saved, previous_assignee, actor_id)  # only after commit
```

And the test that pins the order, written before the implementation:

```python
def test_create_with_assignee_dispatches_after_commit(service, dispatcher) -> None:
    task = service.create(ALICE, TaskCreate(title="x", assignee_id=BOB))

    assert dispatcher.calls == [(task.id, BOB)]
    assert dispatcher.commits_at_call == [1]  # the commit had already happened
```

## 3. How the output was validated

1. **Tests first.** A test that passed before the implementation existed was treated as a problem with the test.
2. **Automated gates on every commit.** ruff, mypy in strict mode, oxlint, and an 80% coverage gate.
3. **Running the real system.** I used the Docker stack and the browser at desktop and phone widths, and now `scripts/smoke.sh` runs in CI as well. Scheduling and proxy bugs only appeared there.
4. **Independent reviews.** Fresh agents, not the one that wrote the code, looked for reasons to reject the work. Every finding was reproduced before it was fixed.

## 4. What was corrected, and what caught it

| What was wrong | What caught it | Fix |
|---|---|---|
| Status compared with `is TaskStatus.DONE`. A plain `"done"` string was stored but `completed_at` was never set. | Repository test | The domain coerces and validates status. |
| SQLite returned naive datetimes. | Round-trip test | A `UTCDateTime` column type. |
| slowapi binds its configuration at import time, which conflicts with the app factory. | Per-test settings | A small dependency built on `limits`. |
| Celery Beat interval jobs first run only after one full interval. | Live run: the demo showed no overdue notifications | A scan when Beat starts (safe to run twice). |
| Ids larger than PostgreSQL `INTEGER` returned 500. | Review 1 (SQLite tests could not see it) | Ids are range-checked at the edge and return 422. |
| A broker outage after commit returned 500, inviting a retry that duplicated the task. It also hung for 65 s. | Review 1, then measured live | Dispatch failures are logged. The result backend was removed. 65.6 s → 3.8 s. |
| A YAML folded block dropped `--proxy-headers`, so every user shared nginx's rate-limit bucket. | Review 1 suspected header spoofing; the logs showed the real cause | An explicit command list. nginx overwrites `X-Forwarded-For`, and the API is reachable only through nginx. |
| Login skipped Argon2 for unknown emails, so response timing revealed which accounts exist. | Review 2 | Unknown emails are checked against a dummy hash. |
| Two routers built repositories directly, outside the composition root. | Review 2 | All wiring goes through `deps.py` and use cases. |
| Login and register shared a 5/min bucket, so a demo switching users hit 429. | Review 2 | Separate limits: login 10/min, register 5/min. |
| `acks_late` combined with a non-idempotent job could duplicate a notification on redelivery. | Review 2 | The assignment job is acknowledged on receipt (at-most-once); the scan keeps `acks_late`. |
| `assert` was used as a runtime guard; it is stripped by `python -O`. | Review 2 | Explicit checks (`persisted_id`). |

## 5. Edge cases, authentication and validation

- **Two layers of validation.**
  - Pydantic checks shape at the edge (422).
  - The domain enforces invariants: non-blank title, valid status, permissions.
  - The UI only hides buttons; the API returns 403 regardless.
- **Tested edge cases:**
  - an inverted date range (422);
  - inclusive range boundaries;
  - an unknown assignee (422);
  - ids outside the database range (422);
  - `limit` outside 1–100;
  - `offset` past the end;
  - `PATCH` with `null` versus an omitted field;
  - an unknown task (404).
- **Tokens.** Expired, malformed, tampered, `alg: none`, and a deleted user's token all return 401 with `WWW-Authenticate: Bearer`, never 500.
- **Login.** The same message and the same hashing work for an unknown email and a wrong password.
- **Worker.** A job for a task that was deleted or reassigned does nothing. Repeated overdue scans don't duplicate notifications. A broker outage never fails the API request.

## 6. Takeaways

**Where the AI was fast:**
- boilerplate: schemas, routers, mappers, Dockerfiles;
- a coherent plan.

**Where it was weakest** (where software usually breaks):
- values crossing boundaries: strings versus enums, naive versus aware datetimes;
- framework lifecycles: decorator binding time, the scheduler's first run;
- deployment details: YAML folding, proxy headers;
- security subtleties: timing leaks.

**What caught all of these:** tests written first, strict static checks, running the real stack, and reviewers who did not write the code. A green suite alone would have shipped three reachable 500s and a broken rate limit.
