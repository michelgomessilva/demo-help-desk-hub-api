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

configure_structlog()
logger = get_logger(__name__)

def create_app() -> FastAPI:
    """
    Factory function que cria e configura a aplicação FastAPI.

    Cria a instância principal e registra todos os routers.

    Returns:
        FastAPI: a aplicação configurada e pronta a usar
    """
    # 👈 Novo! Validar secrets na startup
    secret_key = os.getenv("SECRET_KEY")

    if not secret_key:
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
        raise ValueError(f"❌ ERRO: ALGORITHM inválido: {algorithm}")

    print("[OK] Secrets validados na startup")

    app = FastAPI(
        title="HelpDesk Hub API",
        description="API para gerenciamento de chamados de suporte técnico.",
        version="1.0.0",
    )

    # 👈 Novo! Configurar CORS
    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "production":
        # 👈 Produção: apenas domínios específicos
        allowed_origins = [
            "https://app.exemplo.com",
            "https://www.exemplo.com",
        ]
    else:
        # 👈 Desenvolvimento: mais permissivo
        allowed_origins_str = os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:8000"
        )
        allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,           # 👈 Permitir cookies
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Content-Type", "Authorization"],
    )

    app.add_middleware(LoggingMiddleware)

    # 👈 Novo! Headers de segurança HTTP
    secure_headers = secure.Secure()

    @app.middleware("http")
    async def set_secure_headers(request, call_next):
        response = await call_next(request)
        response.headers.update(secure_headers.headers)
        return response

    # Registar routers (agrupamentos de rotas)
    app.include_router(system_routes.router)       # GET /, GET /health
    app.include_router(ticket_routes.router)       # Operações com tickets
    app.include_router(categories_routes.router)   # GET /categories
    app.include_router(auth_routes.router)         # 👈 Novo! Auth routes

    return app


# Criar a instância global que o uvicorn vai usar
app = create_app()

# SEMANA 4: Criar tabelas na base de dados ao iniciar
# Isto garante que as tabelas existem quando a app começa
# Em produção, deverias usar Alembic para migrações em vez disto
try:
    from src.infrastructure.database import Base, engine
    Base.metadata.create_all(bind=engine)
except Exception as e:
    # Se falhar (ex: BD não configurada), continua com InMemory
    print(f"Aviso: Não foi possível criar tabelas: {e}")
    print("A aplicação vai usar o repositório em memória.")
