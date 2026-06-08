from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.api.schemas.responses.root_response import RootResponse
from src.api.schemas.responses.health_response import HealthResponse, ReadinessResponse
from src.infrastructure.database import engine
from src.infrastructure.logging_config import get_logger

# 👈 Obter logger estruturado
logger = get_logger(__name__)

router = APIRouter()


@router.get("/", response_model=RootResponse)
def read_root() -> RootResponse:
    # 👈 Debug: endpoint raiz acessado
    logger.debug("root_endpoint_accessed")
    return RootResponse(
        name="HelpDesk Hub API",
        status="ok",
        docs="/docs",
    )


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """
    Liveness — a aplicação está viva?

    Verificação simples, sem dependências externas. Mantida compatível com o
    HEALTHCHECK do Docker (devolve {"status": "healthy"}).
    """
    # 👈 Debug: health check executado
    logger.debug("health_check_endpoint_accessed")
    return HealthResponse(status="healthy")


@router.get("/health/live", response_model=HealthResponse)
def liveness() -> HealthResponse:
    """Liveness explícito (alias de /health) — não toca em dependências externas."""
    logger.debug("liveness_endpoint_accessed")
    return HealthResponse(status="healthy")


@router.get("/health/ready", response_model=ReadinessResponse)
def readiness() -> JSONResponse:
    """
    Readiness — a aplicação está pronta a servir tráfego?

    Valida a ligação à base de dados executando `SELECT 1`.
    - BD OK  -> 200 {"status": "ready", "checks": {"database": "ok"}}
    - BD KO  -> 503 {"status": "not_ready", "checks": {"database": "error: ..."}}
    """
    checks: dict[str, str] = {}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
        logger.debug("readiness_check_passed")
        body = ReadinessResponse(status="ready", checks=checks)
        return JSONResponse(status_code=200, content=body.model_dump())
    except Exception as e:
        checks["database"] = f"error: {e}"
        logger.warning("readiness_check_failed", error=str(e))
        body = ReadinessResponse(status="not_ready", checks=checks)
        return JSONResponse(status_code=503, content=body.model_dump())
