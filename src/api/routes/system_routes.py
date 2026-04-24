from fastapi import APIRouter

from src.api.schemas.responses.root_response import RootResponse
from src.api.schemas.responses.health_response import HealthResponse

router = APIRouter()

@router.get("/", response_model=RootResponse)
def read_root() -> RootResponse:
    return RootResponse(
        name="HelpDesk Hub API",
        status="ok",
        docs="/docs",
    )


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="healthy")
