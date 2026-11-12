# Presentation: thought process

This document explains how I approached the exercise: how I read the requirements, which decisions I made and why, how the work was organised, and what I would do next. It doubles as the script for the live presentation.

## 1. User story

> **As a** member of a small team,
> **I want to** create tasks with due dates, assign them to teammates and track their status,
> **so that** nothing slips and everyone knows what they own.

Acceptance criteria:

1. I can sign up, sign in, and stay signed in until my token expires.
2. I can create, view, edit and delete tasks. Only the owner can delete; the owner or the assignee can edit.
3. I can assign a task to a teammate, and they get a notification.
4. I can mark a task as completed.
5. I can filter by status, due-date range and assignee, and page through results.
6. Overdue tasks are visibly flagged, and their owner or assignee is notified once.
7. It works on a phone.

## 2. Reading the requirements

I first listed every explicit requirement (CRUD, assignment, completion, filters, JWT, pagination, PostgreSQL/SQLite, tests ≥ 80%, Docker, Swagger, `pyproject.toml` + pre-commit, rate limiting, Celery + Redis, a responsive frontend with CRUD, seed data, a GenAI write-up). I then looked for what the brief leaves open, because those gaps are where design decisions live:

| Ambiguity | How I resolved it |
|---|---|
| Who can see or edit which tasks? | A team board: everyone signed in sees all tasks, the owner or assignee edits, and only the owner deletes. The rule lives in the domain (`Task.can_edit` / `can_delete`), so changing it touches one place. |
| What should the background worker do? | Two real jobs you can see in the demo: an event-driven *assignment notification* and a scheduled *overdue scan* that skips tasks already notified. |
| "Filter by due date": exact day or range? | An inclusive range (`due_after`, `due_before`) plus `assignee_id`. An inverted range is a 422, not an empty list. |
| Is "unit tests for critical endpoints" unit or integration? | Both: unit tests for the rules and use cases (fast, with fakes) and integration tests for every endpoint. |
| Swagger "(FastAPI)" vs drf-yasg "(Django)" | I picked FastAPI (see §3). Its OpenAPI 3 docs are generated from the type hints. |
| What does "mark as completed" record? | Status `done` plus a `completed_at` timestamp maintained by the domain (cleared if the task is reopened). There is a dedicated `POST /tasks/{id}/complete` that expresses the intent, besides the generic `PATCH`. |

## 3. Main design decisions and trade-offs

**FastAPI + Clean Architecture.** The evaluation names Clean Architecture explicitly. Django's natural path (fat models on the ORM) couples business rules to persistence. FastAPI imposes no structure, and its `Depends` system is dependency injection out of the box. The backend has four layers, `domain` → `application` → `infrastructure` / `api`, with one rule: imports only point inward. Use cases depend on `Protocol` ports, which lets me test them in milliseconds with in-memory fakes.

**Commit before enqueue (the part I'd highlight in review).** If the API enqueued the Celery job *before* committing, the worker could pick it up before the row exists, or notify about a task whose transaction later rolled back. So repositories only `flush()`, the use case decides when to `commit()` through a Unit of Work port, and the dispatcher is called *after* the commit. A unit test (`test_create_with_assignee_dispatches_after_commit`) pins this order.

The final review raised the other side of this: if Redis is down *after* the commit, the old code returned a 500, so the client would retry and create a duplicate task. Now the request succeeds and the failure is logged (`test_broker_failure_after_commit_does_not_fail_the_request`). Measuring it live also showed a 65-second hang, caused by an unused Celery result backend; removing it brought a dead-broker enqueue down to a few seconds. The remaining gap, a lost notification, is what a **transactional outbox** solves; it is listed as the next step.

**Sync SQLAlchemy.** FastAPI runs sync endpoints in a thread pool, Celery is sync, and the load is small. Async would add complexity (lazy-loading pitfalls, async fixtures) without a measurable benefit here. The repository ports isolate the choice.

**Dates.** `due_date` is a calendar `date` (a deadline is a day, not an instant), and all timestamps are timezone-aware UTC. SQLite drops timezone info, so a small `UTCDateTime` column type normalises values in and out. A test caught that.

**Security.** Argon2id hashing; the same "invalid credentials" message for unknown email and wrong password; a JWT secret of at least 32 bytes enforced at startup; algorithms pinned when decoding (rejects `alg: none`); 401 responses always carry `WWW-Authenticate: Bearer`; stricter rate limits on login and register; ids validated to the database's integer range (no 500s on overflow); containers run as non-root; no secrets in the repo. The API is reachable only through nginx, which overwrites `X-Forwarded-For` with the real peer address, so per-IP limits cannot be spoofed.

**Rate limiting.** Redis-backed counters shared by every API replica: 100 req/min per IP by default and 5 req/min on login/register. I started with slowapi, but its decorators bind configuration at import time, which fought the app factory and per-test settings. I switched to the library it uses internally (`limits`) behind a small FastAPI dependency.

**Frontend state.** Server data lives in TanStack Query (cache and invalidation after mutations), filters and page in the URL, UI state locally, and the session in an `AuthContext`. A 401 anywhere clears the token and returns to the login page. nginx proxies `/api`, so the app and the API share an origin: no CORS and no console warnings.

## 4. How I worked

1. **Plan first.** I wrote an implementation plan with exact interfaces between layers and the test list for each step, before any code.
2. **TDD per step.** For each task: write the failing tests, watch them fail for the right reason, implement the minimum, then run the full suite. The git history shows this rhythm in small commits.
3. **Gates on every commit.** pre-commit runs ruff (lint + format), mypy (strict) and oxlint. CI repeats them and builds the Docker images.
4. **Independent review.** A fresh reviewer read the whole branch adversarially. Its findings (integer overflow → 500, broker outage → 500, rate-limit keying, empty page after delete) were each reproduced, fixed test-first and re-verified live. One of them turned out to have a different root cause than reported: a YAML folded block had silently dropped `--proxy-headers`.
5. **Run the real thing.** After the backend was done, I ran the whole stack in Docker and exercised it end to end: login, assign a task, watch the worker log, see Bob's notification. Then the same in a browser at desktop and 375 px widths, with the console open. This surfaced one issue the tests could not: Celery Beat interval jobs first fire only after one full interval, so I added a scan on beat start-up.

## 5. Demo script (≈ 10 minutes)

1. `docker compose up --build`, then open http://localhost:5173.
2. Sign in as **alice@example.com / demo1234**. Point out the overdue badges and the notifications panel (filled by the start-up overdue scan).
3. Create a task, assign it to **Bob**, and set a due date.
4. Filter by status, assignee and date range. Note that the URL changes, so the filtered view can be shared or reloaded. Page through results.
5. Complete a task, edit another, and try to delete a task Alice doesn't own (no button: the rule also exists server-side, returning 403).
6. Sign out, sign in as **bob@example.com**: the assignment notification is there. Show the worker log line.
7. Shrink the browser to phone width. Open DevTools to show a clean console.
8. Open http://localhost:5173/docs, **Authorize**, and call `GET /tasks` with filters. Show a 422 for an inverted date range.
9. Run `uv run pytest` to show 117 tests and the coverage report.

## 6. With more time

- Refresh tokens in httpOnly cookies, and token revocation (a `jti` denylist in Redis).
- A transactional outbox for guaranteed notification delivery.
- WebSockets or SSE instead of 30-second polling.
- Teams/projects and role-based permissions.
- Integration tests on PostgreSQL with Testcontainers; end-to-end tests with Playwright.
- Observability: structured logs with request IDs, metrics and tracing.
