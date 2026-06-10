---
name: create-migration
description: Create and apply an Alembic database migration for the HelpDesk Hub API after editing a SQLAlchemy ORM model. Use when the user adds/changes/removes a column, table, index, or constraint and needs a migration (e.g. "create a migration", "add a column to tickets/users", "migrate the schema"). Guides the autogenerate → review → upgrade workflow safely.
disable-model-invocation: true
---

# create-migration

Safely create and apply an Alembic migration in this repo. Migrations run via
`uv run alembic ...`; the URL comes from `DATABASE_URL` (read in `migrations/env.py`).
**Never** use `Base.metadata.create_all` as the migration path — that's a dev-only
convenience in `src/main.py`.

Track these steps with TodoWrite and do them in order.

## 1. Preconditions
- `.env` exists with a valid `DATABASE_URL` (Postgres). Confirm it's set.
- The database is reachable. If using the local stack:
  ```bash
  docker compose up -d postgres
  ```
- Optional sanity check of current state:
  ```bash
  uv run alembic current
  uv run alembic history
  ```

## 2. Confirm the ORM change is visible to autogenerate
- The model edit must be in `src/infrastructure/models/` (e.g. `ticket_orm.py`, `user_orm.py`).
- The model's class **must be imported in `migrations/env.py`** (it imports
  `TicketORM, CommentORM, UserORM` so `Base.metadata` sees them). If you added a **new**
  model class/table, add its import to `migrations/env.py` first — otherwise autogenerate
  produces an empty migration.

## 3. Generate the migration
Use a short, imperative message describing the change:
```bash
uv run alembic revision --autogenerate -m "add <field> to <table>"
```
This writes a new file to `migrations/versions/<rev>_<slug>.py`.

## 4. Review the generated file (do not trust autogenerate blindly)
Open the new file and verify, or delegate to the **migration-reviewer** subagent
(`Use the migration-reviewer agent to review the new migration`). Check:
- No unintended `op.drop_*` (autogenerate sometimes drops things it shouldn't, e.g. on
  `Enum`/`server_default` diffs).
- `add_column(nullable=False)` includes a `server_default` (else it fails on existing rows).
- No type changes that **narrow** a column (truncation risk).
- `downgrade()` mirrors `upgrade()` in reverse order (repo convention: index → constraint
  → column), and isn't a bare `pass`.
- New FKs set a sensible `ondelete` (repo uses `SET NULL`).

## 5. Adjust if needed
Hand-edit `upgrade()`/`downgrade()` to fix anything from step 4 (add `server_default`,
remove spurious ops, complete the downgrade). Re-read after editing.

## 6. Apply and confirm
```bash
uv run alembic upgrade head
uv run alembic current      # should show the new revision as head
```
To roll back the last migration during testing:
```bash
uv run alembic downgrade -1
```

## Notes
- One logical change per migration; keep the message descriptive.
- Don't edit a migration that's already applied in a shared/remote environment — create a
  new one instead.
- Commit the model change and the migration file together.
