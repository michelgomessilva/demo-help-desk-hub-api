"""
Aplicação FastAPI principal.

Este é o ponto de entrada da aplicação. Aqui criamos a instância do FastAPI
e registamos todos os routers (rotas).

Por que um ficheiro separado?
- Mantém main.py limpo e focado
- Facilita testes (podemos chamar create_app() com configuração diferente)
- Padrão de factory: permite criar a aplicação em diferentes contextos
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import secure
from dotenv import load_dotenv

from src.api.routes import system_routes
from src.api.routes import ticket_routes
from src.api.routes import categories_routes
from src.api.routes import auth_routes
from src.infrastructure.logging_config import configure_structlog, get_logger
from src.infrastructure.middleware.logging_middleware import LoggingMiddleware

# 👈 Carregar variáveis de ambiente
load_dotenv()

# 👈 Configurar logging estruturado (primeira coisa!)
configure_structlog()
logger = get_logger(__name__)


def create_app() -> FastAPI:
    """
    Factory function que cria e configura a aplicação FastAPI.

    Cria a instância principal e registra todos os routers.

    Returns:
        FastAPI: a aplicação configurada e pronta a usar
    """
    # 👈 Validar secrets na startup
    secret_key = os.getenv("SECRET_KEY")

    if not secret_key:
        logger.error(
            "startup_failed",
            reason="SECRET_KEY not configured",
            error_code="CONFIG_ERROR"
        )
        raise ValueError(
            "❌ ERRO: SECRET_KEY não configurada no .env\n"
            "Execute: openssl rand -hex 32"
        )

    if len(secret_key) < 32:
        logger.error(
            "startup_failed",
            reason="SECRET_KEY too short",
            min_length=32,
            actual_length=len(secret_key),
            error_code="CONFIG_ERROR"
        )
        raise ValueError(
            "❌ ERRO: SECRET_KEY muito curta (mínimo 32 caracteres)\n"
            "Execute: openssl rand -hex 32"
        )

    algorithm = os.getenv("ALGORITHM", "HS256")
    if algorithm not in ["HS256", "HS512"]:
        logger.error(
            "startup_failed",
            reason="invalid algorithm",
            algorithm=algorithm,
            valid_algorithms=["HS256", "HS512"],
            error_code="CONFIG_ERROR"
        )
        raise ValueError(f"❌ ERRO: ALGORITHM inválido: {algorithm}")

    logger.info("startup_validation_passed", secret_key_length=len(secret_key), algorithm=algorithm)

    app = FastAPI(
        title="HelpDesk Hub API",
        description="API para gerenciamento de chamados de suporte técnico.",
        version="1.0.0",
    )

    # 👈 Configurar CORS
    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "production":
        # 👈 Produção: apenas domínios específicos
        allowed_origins = [
            "https://app.exemplo.com",
            "https://www.exemplo.com",
        ]
        logger.debug("cors_configured", mode="production", origins_count=len(allowed_origins))
    else:
        # 👈 Desenvolvimento: mais permissivo
        allowed_origins_str = os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:8000"
        )
        allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]
        logger.debug("cors_configured", mode="development", origins_count=len(allowed_origins))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Content-Type", "Authorization"],
    )

    # 👈 Adicionar middleware de logging HTTP (ANTES do secure headers)
    app.add_middleware(LoggingMiddleware)

    # 👈 Headers de segurança HTTP
    secure_headers = secure.Secure()

    @app.middleware("http")
    async def set_secure_headers(request, call_next):
        response = await call_next(request)
        response.headers.update(secure_headers.headers)
        return response

    # 👈 Evento de startup da aplicação
    @app.on_event("startup")
    async def startup_event():
        logger.info(
            "application_startup",
            app_name="HelpDesk Hub API",
            version="1.0.0",
            environment=environment
        )

    # 👈 Evento de shutdown da aplicação
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("application_shutdown", app_name="HelpDesk Hub API")

    # Registar routers (agrupamentos de rotas)
    app.include_router(system_routes.router)       # GET /, GET /health
    app.include_router(ticket_routes.router)       # Operações com tickets
    app.include_router(categories_routes.router)   # GET /categories
    app.include_router(auth_routes.router)         # Auth routes

    logger.debug("routers_registered", routers_count=4)

    # 👈 Observabilidade (OpenTelemetry): traces + métricas + instrumentação.
    # Graceful: se a stack estiver desligada (sem OTEL_EXPORTER_OTLP_ENDPOINT),
    # esta chamada não tem efeito e a app continua a funcionar normalmente.
    try:
        from src.infrastructure.database import engine
        from src.infrastructure.observability import configure_observability

        configure_observability(app, engine=engine)
    except Exception as e:
        logger.warning("observability_setup_skipped", error=str(e))

    return app


# Criar a instância global que o uvicorn vai usar
app = create_app()

# 👈 Criar tabelas na base de dados ao iniciar
# Isto garante que as tabelas existem quando a app começa
# Em produção, deverias usar Alembic para migrações em vez disto
try:
    from src.infrastructure.database import Base, engine
    logger.debug("database_initialization_started", database_url=os.getenv("DATABASE_URL", "sqlite"))
    Base.metadata.create_all(bind=engine)
    logger.info("database_tables_created_successfully")
except Exception as e:
    # Se falhar (ex: BD não configurada), continua com InMemory
    logger.warning(
        "database_initialization_failed",
        error=str(e),
        fallback="in_memory_repository"
    )
    print(f"Aviso: Não foi possível criar tabelas: {e}")
    print("A aplicação vai usar o repositório em memória.")
