"""
Aplicação FastAPI principal.

Este é o ponto de entrada da aplicação. Aqui criamos a instância do FastAPI
e registamos todos os routers (rotas).

Por que um ficheiro separado?
- Mantém main.py limpo e focado
- Facilita testes (podemos chamar create_app() com configuração diferente)
- Padrão de factory: permite criar a aplicação em diferentes contextos
"""

from fastapi import FastAPI
from src.api.routes import system_routes
from src.api.routes import ticket_routes
from src.api.routes import categories_routes


def create_app() -> FastAPI:
    """
    Factory function que cria e configura a aplicação FastAPI.

    Cria a instância principal e registra todos os routers.

    Returns:
        FastAPI: a aplicação configurada e pronta a usar
    """
    app = FastAPI(
        title="HelpDesk Hub API",
        description="API para gerenciamento de chamados de suporte técnico.",
        version="1.0.0",
    )

    # Registar routers (agrupamentos de rotas)
    app.include_router(system_routes.router)       # GET /, GET /health
    app.include_router(ticket_routes.router)       # Operações com tickets
    app.include_router(categories_routes.router)   # GET /categories

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

