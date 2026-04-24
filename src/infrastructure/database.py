"""
Configuração da base de dados com SQLAlchemy.

Este ficheiro:
1. Carrega variáveis de ambiente
2. Cria a engine de SQLAlchemy
3. Define a session factory
4. Fornece a classe base para todos os models ORM

Por que separar isto?
- Centraliza a configuração de banco de dados
- Reutilizável em testes, migrações, etc.
- Fácil de alterar (string de conexão, pool, etc.)
"""

from dotenv import load_dotenv
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool

# Carregar variáveis do ficheiro .env
load_dotenv()

# Obter a URL da base de dados da variável de ambiente
DATABASE_URL = os.getenv("DATABASE_URL")

# Criar a engine (conexão com o banco)
# echo=True apenas em desenvolvimento para ver SQL
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("ENVIRONMENT") == "development",
    pool_pre_ping=True,  # Verificar conexão antes de usar
)

# Factory para criar sessões
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """
    Classe base para todos os modelos ORM.

    Todos os models (TicketORM, CommentORM, etc.) devem herdar desta.
    SQLAlchemy usa isto para mapping automático.
    """
    pass


def get_db_session():
    """
    Dependency injection para FastAPI.

    Uso em rotas:
        @router.get("/tickets")
        def list_tickets(db: Session = Depends(get_db_session)):
            # Usar db aqui
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
