# CLAUDE.md

HelpDesk Hub API — FastAPI + SQLAlchemy ticket/support API with layered (Clean)
architecture, Repository pattern, JWT auth, structured logging (structlog) and
OpenTelemetry. Package/dependency manager is **uv**. Code comments and docstrings
are in Portuguese — match that when editing.

## Commands

Prereqs: Python 3.11+, `uv` installed. A `.env` is required to run/test (see
[.env.example](.env.example)); at minimum `SECRET_KEY` (≥32 chars) and
`DATABASE_URL` must be set, or `create_app()` raises at startup.

```bash
# Install deps (runtime + dev group)
uv sync --all-extras --dev

# Run the API (reads .env; serves on http://localhost:8000, docs at /docs)
uv run uvicorn src.main:app --reload

# Run tests (pytest config in pytest.ini; asyncio_mode=auto)
uv run pytest                       # all tests, verbose
uv run pytest tests/test_domain.py  # single file
uv run pytest -m unit               # by marker: unit | integration | slow

# Database migrations (Alembic; needs DATABASE_URL)
uv run alembic upgrade head         # apply all
uv run alembic revision --autogenerate -m "msg"   # after editing an ORM model
uv run alembic current | uv run alembic history | uv run alembic downgrade -1

# Full local stack (API + Postgres + OTel/Grafana/Tempo/Loki/Prometheus)
docker compose up --build           # see DOCKER.md and OBSERVABILITY.md
```

CI runs `uv sync --all-extras --dev` then `uv run pytest` against a Postgres 16
service — see [.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml).

> **Format/Lint:** no formatter or linter is configured or installed in this repo.
> [.vscode/settings.json](.vscode/settings.json) enables editor pylint + format-on-save only.
> TODO: if lint/format is desired, add and pin a tool (the README suggests
> `ruff`/`black`/`mypy`) and document the exact command here once it exists.

## Architecture

Layered architecture; dependencies point inward (API → Application → Domain;
Infrastructure implements Domain interfaces). The Domain layer imports nothing
from FastAPI/SQLAlchemy.

| Layer | Path | Responsibility |
|-------|------|----------------|
| API | [src/api/routes/](src/api/routes/) | HTTP only: parse request, validate, call service, map domain exceptions → HTTP status, return JSON. |
| API schemas | [src/api/schemas/](src/api/schemas/) | Pydantic request/response models (`requests/`, `responses/`). Generic `PaginatedResponse[T]`. |
| Application | [src/application/](src/application/) | Business logic. [ticket_service.py](src/application/ticket_service.py), [auth_service.py](src/application/auth_service.py). Raises domain exceptions, never HTTP. |
| Domain | [src/domain/tickets/](src/domain/tickets/) | Pure core: [models.py](src/domain/tickets/models.py) (dataclasses), [enums.py](src/domain/tickets/enums.py), [exceptions.py](src/domain/tickets/exceptions.py), [repositories.py](src/domain/tickets/repositories.py) (`ITicketRepository` ABC). |
| Infrastructure | [src/infrastructure/](src/infrastructure/) | Technical details: DB engine, ORM models, repository impls, DI wiring, JWT, logging, middleware, OTel. |
| Composition root | [src/main.py](src/main.py) | `create_app()` factory: env validation, CORS, middleware, router registration, observability. |
| Migrations | [migrations/](migrations/) | Alembic versions. |
| Tests | [tests/](tests/) | pytest; fixtures in [tests/conftest.py](tests/conftest.py). |

Request flow (authenticated ticket endpoint):

```
HTTP request
  → route (src/api/routes/ticket_routes.py)
      Security(get_current_user)  → JWT auth (infrastructure/di/auth_dependencies.py)
      Depends(get_service)        → DI (infrastructure/di/dependencies.py)
                                       get_repository → SQLAlchemyTicketRepository(db session)
  → TicketService (application)   → business rules, raises TicketNotFoundError / ValueError
  → ITicketRepository (domain interface) ← implemented in infrastructure/repositories/
  → route maps domain exception → HTTPException(404/400); returns Pydantic response_model
```

## Key Patterns

- **Repository pattern / DIP.** Interface `ITicketRepository` lives in the domain
  ([repositories.py](src/domain/tickets/repositories.py)); implementations live in
  infrastructure ([sqlalchemy_ticket_repository.py](src/infrastructure/repositories/sqlalchemy_ticket_repository.py),
  [in_memory_ticket_repository.py](src/infrastructure/repositories/in_memory_ticket_repository.py)).
  Services depend only on the interface. **Swap the data source in one place only:**
  `get_repository()` in [dependencies.py](src/infrastructure/di/dependencies.py).
- **Dependency Injection via FastAPI.** Routes never construct services/repos; they
  use `Depends(get_service)` / `Security(get_current_user)`. DB sessions come from
  `Depends(get_db_session)` ([database.py](src/infrastructure/database.py)) and are
  closed per-request.
- **Exception boundary.** Application/domain raise domain exceptions
  (`TicketNotFoundError`) or `ValueError`; **only routes** translate them to
  `HTTPException`. Never raise HTTP errors below the API layer.
- **Validation with Pydantic.** All input is a request schema in
  [schemas/requests/](src/api/schemas/requests/); all output declares a
  `response_model` from [schemas/responses/](src/api/schemas/responses/).
- **Domain enums are the source of truth.** `TicketStatus` / `TicketPriority` /
  `TicketCategory` are `str`-Enums in [enums.py](src/domain/tickets/enums.py); use
  them, not raw strings.
- **Structured logging.** Get a logger with
  `get_logger(__name__)` ([logging_config.py](src/infrastructure/logging_config.py))
  and log events as `logger.info("event_name", key=value, ...)` (snake_case event +
  kwargs). HTTP requests are logged by [logging_middleware.py](src/infrastructure/middleware/logging_middleware.py).
- **App factory.** Create the app via `create_app()`; tests instantiate it fresh.
  Do not add module-level side effects that assume a configured environment.
- **Observability is graceful.** OTel setup is wrapped so the app still runs when the
  telemetry stack/`OTEL_EXPORTER_OTLP_ENDPOINT` is absent. See [OBSERVABILITY.md](OBSERVABILITY.md).

## Code Quality Rules

### (a) Tooling / configs that actually exist

- **Python 3.11+** required ([pyproject.toml](pyproject.toml), [.python-version](.python-version)).
  Modern typing is the norm: `X | None`, `list[X]`, `tuple[...]`.
- **pytest** config in [pytest.ini](pytest.ini): `testpaths=tests`, `--strict-markers`,
  `asyncio_mode=auto`, markers `unit`/`integration`/`slow`.
- **Alembic** for all schema changes ([alembic.ini](alembic.ini), [migrations/](migrations/));
  never hand-edit the DB schema. `create_all()` in main.py is a dev convenience, not the
  migration path.
- **No type checker, linter, formatter, pre-commit, or warnings-as-errors is configured.**
  Do not claim these pass — there is nothing to run. (See Format/Lint TODO above.)

### (b) Non-negotiable code principles (humans and AI)

- **Respect the layers.** No HTTP/DB imports in domain; no business logic in routes;
  no domain logic in repositories. If a change crosses layers, stop and reconsider.
- **SOLID & DRY.** One responsibility per class/function. Depend on `ITicketRepository`,
  not concretions. Reuse generics like `PaginatedResponse[T]`; don't copy-paste mappings.
- **Guard clauses first.** Validate and return/raise early (see `TicketService.create_ticket`);
  avoid deep nesting.
- **Explicit error handling.** Raise specific domain exceptions/`ValueError` with clear
  messages; catch narrowly. **No silent failures** — never swallow an exception without
  logging it and either re-raising or returning a defined result. The OTel try/except in
  main.py is the only intentional best-effort fallback, and it logs a warning.
- **Clear names, type hints everywhere.** Public functions are typed and have docstrings
  (Portuguese, matching existing style).
- **Production-ready & testable.** New business logic goes in a service and is unit-tested
  against a mock/in-memory repository; new endpoints get an integration test via
  `TestClient`. No secrets, connection strings, or tokens in code or logs — read them from
  env (`os.getenv`) per [.env.example](.env.example).

## Spec-Driven Development

Workflow not yet defined in this repo. TODO: see `docs/spec-driven-development.md`
(to be created — referenced by prompt 07).

## Claude Code Automations

### Skills (`.claude/skills/`)
- **`create-migration`** ([SKILL.md](.claude/skills/create-migration/SKILL.md)) — user-only.
  Guides the Alembic workflow: edit ORM → `uv run alembic revision --autogenerate` → review
  → `upgrade head`. Invoke when changing the DB schema.
- **`new-endpoint`** ([SKILL.md](.claude/skills/new-endpoint/SKILL.md)) — scaffolds a full
  vertical slice (domain → application → infrastructure → API) for a new resource, mirroring
  the tickets slice and the layer rules above.

### Subagents (`.claude/agents/`)
- **`security-reviewer`** ([agent](.claude/agents/security-reviewer.md)) — read-only audit of
  changes for this repo's fragile invariants: broken access control (auth-only ticket routes,
  no ownership/role check), PII/LGPD leakage in logs/responses, JWT/secret handling, CORS.
  Dispatch before a PR or after auth/ticket/user changes.
- **`migration-reviewer`** ([agent](.claude/agents/migration-reviewer.md)) — read-only review
  of autogenerated Alembic migrations for destructive ops, NOT NULL adds without
  `server_default`, downgrade correctness, and models missing from `migrations/env.py`.
  Used by the `create-migration` skill.

### MCP Servers ([.mcp.json](.mcp.json))
Project-scoped; secrets injected via `${VAR}` from the environment (`.env`), never committed.
- **context7** (`npx`) — live docs for FastAPI/SQLAlchemy/Alembic/Pydantic/OTel. No secret.
- **postgres** (`uvx postgres-mcp --access-mode=restricted`) — **read-only** access to the dev
  DB via `${DATABASE_URL}`; inspect `tickets`/`users`/`comments` without ad-hoc scripts.
- **grafana** (`docker run mcp/grafana`) — query the local OTel stack (Tempo/Loki/Prometheus)
  at `${GRAFANA_URL:-http://localhost:3001}`. Requires a Grafana service account token in
  `GRAFANA_SERVICE_ACCOUNT_TOKEN` (create in Grafana → Administration → Service accounts).
- **Prereqs**: Node/`npx`, `uv`/`uvx`, and Docker installed locally. Verify with `claude mcp list`.

### Hooks / Permissions
- Permission allowlist for routine `uv`/`git` commands lives in
  [.claude/settings.local.json](.claude/settings.local.json).
- Edits/reads of `.env*`, secrets, `docker-compose*.yml`, and `alembic.ini` require
  confirmation via the `ask` rules in [.claude/settings.json](.claude/settings.json).
- No automated event hooks are configured. TODO (prompt 09): add a `PostToolUse` hook (e.g.
  `uv run pytest -m unit` after editing `src/**`) once a linter/formatter is adopted.
