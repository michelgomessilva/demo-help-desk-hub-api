"""
Modelos ORM (Object-Relational Mapping) para SQLAlchemy.

Estes models definem a estrutura das tabelas no banco de dados.
São diferentes dos modelos de domínio (Ticket, Comment) porque:
- Herdam de SQLAlchemy Base
- Incluem detalhes técnicos (colunas, tipos SQL, relacionamentos)
- Podem ter hooks de ciclo de vida (before_insert, after_update, etc.)

Por que separados dos models de domínio?
- Domain models são puros (sem conhecimento de banco)
- ORM models sabem de SQL e persistência
- Facilita trocar o banco sem tocar na lógica

Conversão:
    TicketORM (banco) ↔ converter ↔ Ticket (domínio)
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from src.infrastructure.database import Base
from src.domain.tickets.enums import TicketStatus, TicketPriority, TicketCategory


class TicketORM(Base):
    """
    Modelo ORM para a tabela tickets.

    Representa um ticket no banco de dados.
    """

    __tablename__ = "tickets"

    # Colunas
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(5000), nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN, nullable=False)
    priority = Column(Enum(TicketPriority), default=TicketPriority.MEDIUM, nullable=False)
    category = Column(Enum(TicketCategory), default=TicketCategory.SOFTWARE, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # Relacionamento
    comments = relationship(
        "CommentORM",
        back_populates="ticket",
        cascade="all, delete-orphan",  # Se deletar ticket, deleta comentários
        lazy="joined"  # Carregar comentários com o ticket
    )

    def __repr__(self):
        return f"<TicketORM(id={self.id}, title={self.title}, status={self.status})>"


class CommentORM(Base):
    """
    Modelo ORM para a tabela comments.

    Representa um comentário num ticket.
    """

    __tablename__ = "comments"

    # Colunas
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    content = Column(String(5000), nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # Relacionamento
    ticket = relationship("TicketORM", back_populates="comments")

    def __repr__(self):
        return f"<CommentORM(id={self.id}, ticket_id={self.ticket_id})>"
