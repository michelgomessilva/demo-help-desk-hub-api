from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Resposta de liveness — indica apenas que a aplicação está viva."""

    status: str


class ReadinessResponse(BaseModel):
    """
    Resposta de readiness — indica se a aplicação está pronta a servir tráfego.

    Inclui o resultado das verificações às dependências (ex: base de dados).
    """

    status: str
    checks: dict[str, str]
