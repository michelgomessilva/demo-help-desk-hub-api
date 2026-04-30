"""
Modelo ORM para a entidade User.

Representa um usuário no sistema de help desk.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from datetime import datetime
from src.infrastructure.database import Base


class UserORM(Base):
    """
    Modelo ORM para a tabela users.
    
    Campos essenciais para um usuário:
    - id: Identificador único
    - name: Nome do usuário
    - email: Email (único)
    - password_hash: Hash da senha (nunca armazenar senha em texto)
    - role: Papel/função (ADMIN, USER, SUPPORT)
    - is_active: Se o usuário está ativo
    - created_at: Data de criação
    """

    __tablename__ = "users"

    # Colunas
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="USER", nullable=False)  # ADMIN, USER, SUPPORT
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    def __repr__(self):
        return f"<UserORM(id={self.id}, name={self.name}, email={self.email}, role={self.role})>"