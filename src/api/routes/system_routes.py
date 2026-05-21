from fastapi import APIRouter

from src.api.schemas.responses.root_response import RootResponse
from src.api.schemas.responses.health_response import HealthResponse
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
    # 👈 Debug: health check executado
    logger.debug("health_check_endpoint_accessed")
    return HealthResponse(status="healthy")
