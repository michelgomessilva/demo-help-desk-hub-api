---
name: new-endpoint
description: Scaffold a complete vertical slice (domain → application → infrastructure → API) for a new resource or endpoint in the HelpDesk Hub API, following its layered/Clean architecture and Repository pattern. Use when adding a new resource (e.g. "add a Users CRUD", "create an endpoint for X", "new resource") so every layer is wired consistently. Build it for me. Use when adding endpoints.
---

# new-endpoint

Scaffold a new resource across all layers, matching this repo's conventions. The existing
**tickets** slice is the source of truth — mirror it; do not invent new patterns. Use
`<res>` for the lowercase singular (e.g. `category`) and `<Res>` for PascalCase (`Category`).

Track the layers below with TodoWrite. Create files **bottom-up** (domain first, API last)
so each layer's imports already exist.

## Layer map & order

| # | Layer | File | Mirror |
|---|-------|------|--------|
| 1 | Domain model | `src/domain/<res>/models.py` | `src/domain/tickets/models.py` |
| 2 | Domain enums | `src/domain/<res>/enums.py` | `src/domain/tickets/enums.py` |
| 3 | Domain exceptions | `src/domain/<res>/exceptions.py` | `src/domain/tickets/exceptions.py` |
| 4 | Repository interface | `src/domain/<res>/repositories.py` | `src/domain/tickets/repositories.py` |
| 5 | ORM model | `src/infrastructure/models/<res>_orm.py` | `src/infrastructure/models/ticket_orm.py` |
| 6 | Repository impls | `src/infrastructure/repositories/{sqlalchemy,in_memory}_<res>_repository.py` | the ticket repos |
| 7 | Service | `src/application/<res>_service.py` | `src/application/ticket_service.py` |
| 8 | DI wiring | edit `src/infrastructure/di/dependencies.py` | add `get_<res>_repository` → `get_<res>_service` |
| 9 | Request schema | `src/api/schemas/requests/<res>_request.py` | `ticket_request.py` |
| 10 | Response schema | `src/api/schemas/responses/<res>_response.py` | `ticket_response.py` |
| 11 | Routes | `src/api/routes/<res>_routes.py` | `ticket_routes.py` |
| 12 | Register router | edit `src/main.py` | `app.include_router(...)` |
| 13 | Migration | run the **create-migration** skill | — |
| 14 | Tests | `tests/test_<res>_*.py` | use `tests/conftest.py` fixtures |

Add `__init__.py` to any new `src/domain/<res>/` package.

## Non-negotiable conventions (verified in the repo)

- **Imports**: stdlib → third-party → `src.` (absolute imports, e.g. `from src.application...`).
- **Logging**: `logger = get_logger(__name__)` from `src.infrastructure.logging_config`; log
  events as `logger.info("snake_case_event", key=value)`. On exceptions include
  `error=str(e), error_type=type(e).__name__`. Never use f-string log messages.
- **Docstrings in Portuguese**, like the rest of the codebase.
- **Layer purity**: domain imports nothing from FastAPI/SQLAlchemy; service raises domain
  exceptions / `ValueError`, never `HTTPException`; only routes map exceptions to HTTP.

## Templates (concise — adapt fields to the resource)

### 1. Domain model — dataclass
```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class <Res>:
    id: int
    name: str
    created_at: datetime = field(default_factory=datetime.now)
```

### 3. Domain exception — stores context + message
```python
class <Res>NotFoundError(Exception):
    def __init__(self, <res>_id: int):
        self.<res>_id = <res>_id
        super().__init__(f"<Res> with ID {<res>_id} not found")
```

### 4. Repository interface — ABC in the domain
```python
from abc import ABC, abstractmethod
from .models import <Res>

class I<Res>Repository(ABC):
    @abstractmethod
    def create(self, <res>: <Res>) -> <Res>: ...
    @abstractmethod
    def get_by_id(self, <res>_id: int) -> <Res> | None: ...
    # add get_all/update as needed, mirroring ITicketRepository
```

### 5. ORM model — `<Res>ORM(Base)`
```python
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from src.infrastructure.database import Base

class <Res>ORM(Base):
    __tablename__ = "<res>s"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
```
**Also** import this class in `migrations/env.py` so autogenerate detects it.

### 6. SQLAlchemy repository — session + ORM↔domain conversion
```python
class SQLAlchemy<Res>Repository(I<Res>Repository):
    def __init__(self, session: Session):
        self._session = session

    def create(self, <res>: <Res>) -> <Res>:
        orm = <Res>ORM(name=<res>.name)
        self._session.add(orm)
        self._session.commit()
        self._session.refresh(orm)
        logger.info("<res>_created_in_database", <res>_id=orm.id)
        return self._orm_to_domain(orm)

    def _orm_to_domain(self, orm: <Res>ORM) -> <Res>:
        return <Res>(id=orm.id, name=orm.name, created_at=orm.created_at)
```
Provide an `InMemory<Res>Repository` too (mirror `in_memory_ticket_repository.py`) for unit tests.

### 7. Service — business logic, guard clauses, domain exceptions
```python
class <Res>Service:
    def __init__(self, repository: I<Res>Repository):
        self._repository = repository

    def create_<res>(self, name: str) -> <Res>:
        if not name or not name.strip():
            logger.warning("<res>_creation_failed", reason="empty_name")
            raise ValueError("Name cannot be empty")
        return self._repository.create(<Res>(id=0, name=name))
```

### 8. DI wiring — append to `dependencies.py`
```python
def get_<res>_repository(db: Session = Depends(get_db_session)) -> I<Res>Repository:
    return SQLAlchemy<Res>Repository(db)

def get_<res>_service(repository: I<Res>Repository = Depends(get_<res>_repository)) -> <Res>Service:
    return <Res>Service(repository)
```

### 9–10. Schemas (Pydantic v2)
```python
# request
class Create<Res>Request(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

# response
class <Res>Response(BaseModel):
    id: int
    name: str
    created_at: datetime
    class Config:
        from_attributes = True
```
For list endpoints reuse the generic `PaginatedResponse[T]` from
`src/api/schemas/responses/paginated_response.py` (`PaginatedResponse.from_data(...)`).

### 11. Routes — auth + DI + exception→HTTP mapping
```python
router = APIRouter(prefix="/<res>s", tags=["<Res>s"])

@router.post("/", response_model=<Res>Response, status_code=201)
def create_<res>(
    request: Create<Res>Request,
    service: <Res>Service = Depends(get_<res>_service),
    current_user: UserORM = Security(get_current_user),
) -> <Res>Response:
    logger.info("create_<res>_endpoint_called", user_id=current_user.id)
    try:
        return service.create_<res>(name=request.name)
    except ValueError as e:
        logger.warning("create_<res>_validation_error", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except <Res>NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
```
> **Authorization reminder**: `Security(get_current_user)` only authenticates. If a <res>
> is owned by a user or is role-restricted, add an ownership/role check in the route or a
> dependency — do not ship auth-only access to per-user resources (this is the repo's known
> #1 risk). Consider running the **security-reviewer** agent on the new slice.

### 12. Register the router in `src/main.py`
```python
from src.api.routes import <res>_routes
app.include_router(<res>_routes.router)
```

## Finish
1. Run the **create-migration** skill to generate/apply the schema migration.
2. Add tests (`tests/test_<res>_*.py`) using `client` / fixtures from `tests/conftest.py`.
3. Verify the app boots and the endpoint appears:
   ```bash
   uv run uvicorn src.main:app --reload   # then open http://localhost:8000/docs
   uv run pytest
   ```
