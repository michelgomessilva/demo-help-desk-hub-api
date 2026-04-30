"""
Configuração do Alembic para o projeto DemoHelpDeskAPI.

Este script é executado pelo Alembic antes de qualquer operação.
Ele configura:
1. Conexão com o banco de dados (DATABASE_URL do .env)
2. Os models ORM (Base.metadata)
3. O modo online/offline
"""

from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig
from dotenv import load_dotenv
import os
import sys
from pathlib import Path

# 👇 IMPORTANTE: Adicionar src ao path Python
sys.path.insert(0, str(Path(__file__).parent.parent))

# 👇 Carregar variáveis de .env
load_dotenv()

# 👇 Importar a Base do projeto
from src.infrastructure.database import Base

# 👇 OBRIGATÓRIO: Importar TODOS os models para o Alembic detectar
# Se não importar aqui, o Alembic não saberá que existem
from src.infrastructure.models.ticket_orm import TicketORM, CommentORM
from src.infrastructure.models.user_orm import UserORM

# Configuração de logging
config = context.config
fileConfig(config.config_file_name)

# 👇 Dizer ao Alembic quais são os metadata dos models
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Executar migrations em modo 'offline'.
    
    Usado quando não consegue conectar ao banco em tempo real
    (ex: gerar SQL para aplicar depois manualmente).
    """
    url = os.getenv("DATABASE_URL", "sqlite:///./test.db")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Executar migrations em modo 'online'.
    
    Conecta ao banco de dados em tempo real e executa as migrations.
    """
    # 👇 Ler DATABASE_URL do arquivo .env
    url = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


# 👇 Verificar o modo e executar
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()