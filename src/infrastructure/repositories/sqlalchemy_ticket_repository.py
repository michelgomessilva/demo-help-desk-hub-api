"""
Implementação do repositório com SQLAlchemy e PostgreSQL.

Esta implementação segue exatamente a mesma interface (ITicketRepository)
que InMemoryTicketRepository, mas guarda dados em PostgreSQL.

O serviço (TicketService) não muda nada — depende da interface,
não da implementação.

Por que duas implementações?
- Semana 2/3: InMemory para aprender sem banco de dados
- Semana 4: SQLAlchemy para dados persistidos em produção
- Testes: MockRepository para testar sem BD real
"""

from sqlalchemy.orm import Session
from sqlalchemy import asc
from src.domain.tickets.repositories import ITicketRepository
from src.domain.tickets.models import Ticket, Comment
from src.domain.tickets.enums import TicketStatus, TicketPriority, TicketCategory
from src.infrastructure.models.ticket_orm import TicketORM, CommentORM
import math


class SQLAlchemyTicketRepository(ITicketRepository):
    """
    Repositório que guarda tickets em PostgreSQL via SQLAlchemy.

    Cada método converte entre:
    - Modelos de domínio (Ticket, Comment) — usado pelo service
    - Modelos ORM (TicketORM, CommentORM) — usado pelo banco

    Por que converter?
    - Domain models são puros (sem know-how de SQL)
    - ORM models sabem de persistência e relacionamentos
    - Service nunca vê ORM — mantém desacoplado
    """

    def __init__(self, session: Session):
        """
        Construtor com injeção de sessão SQLAlchemy.

        Args:
            session: instância de Session do SQLAlchemy
        """
        self._session = session

    def create(self, ticket: Ticket) -> Ticket:
        """
        Cria um novo ticket na base de dados.

        Processo:
        1. Converter Ticket (domínio) → TicketORM (banco)
        2. Guardar na sessão
        3. Commit para gravar na BD
        4. Converter TicketORM → Ticket (domínio) para retornar

        Args:
            ticket: Ticket do domínio sem ID

        Returns:
            Ticket com ID atribuído pelo banco
        """
        # Guard Clause
        if not ticket:
            raise ValueError("Ticket cannot be None")

        # Converter de domínio para ORM
        ticket_orm = TicketORM(
            title=ticket.title,
            description=ticket.description,
            status=ticket.status,
            priority=ticket.priority,
            category=ticket.category,
        )

        # Guardar na sessão
        self._session.add(ticket_orm)
        # Commit — escreve na BD
        self._session.commit()
        # Refresh — recarrega para ter ID gerado
        self._session.refresh(ticket_orm)

        # Converter de ORM para domínio e retornar
        return self._orm_to_domain(ticket_orm)

    def get_all(
        self,
        status: TicketStatus | None = None,
        priority: TicketPriority | None = None,
        category: TicketCategory | None = None,
        page: int = 1,
        size: int = 10,
    ) -> tuple[list[Ticket], int]:
        """
        Lista tickets com filtros e paginação direto do banco.

        SQLAlchemy faz a filtragem e paginação no SQL (eficiente!)
        em vez de carregar tudo na memória como InMemory faz.

        Args:
            status: filtro opcional
            priority: filtro opcional
            category: filtro opcional
            page: número da página (começa em 1)
            size: items por página

        Returns:
            (lista de Tickets da página, total de Tickets)
        """
        # Guard Clauses
        if page < 1:
            page = 1
        if size < 1 or size > 100:
            size = 10

        # Query base
        query = self._session.query(TicketORM)

        # Aplicar filtros (SQL WHERE)
        if status:
            query = query.filter(TicketORM.status == status)
        if priority:
            query = query.filter(TicketORM.priority == priority)
        if category:
            query = query.filter(TicketORM.category == category)

        # Contar TOTAL antes de paginar
        # (precisa saber quantas páginas existem)
        total = query.count()

        # Ordenar por criação mais recente
        query = query.order_by(TicketORM.created_at.desc())

        # Paginar (LIMIT e OFFSET no SQL)
        skip = (page - 1) * size
        results = query.offset(skip).limit(size).all()

        # Converter ORMs para domínio
        tickets = [self._orm_to_domain(orm) for orm in results]

        return (tickets, total)

    def get_by_id(self, ticket_id: int) -> Ticket | None:
        """
        Obtém um ticket pelo ID.

        Args:
            ticket_id: ID do ticket

        Returns:
            Ticket ou None se não encontrado
        """
        ticket_orm = self._session.query(TicketORM).filter(
            TicketORM.id == ticket_id
        ).first()

        if not ticket_orm:
            return None

        return self._orm_to_domain(ticket_orm)

    def update(self, ticket: Ticket) -> Ticket:
        """
        Atualiza um ticket existente.

        Guard Clauses verificam que o ticket é válido.

        Args:
            ticket: Ticket com dados atualizados (deve ter ID)

        Returns:
            Ticket atualizado

        Raises:
            ValueError: se ticket ou ID são inválidos
        """
        # Guard Clauses
        if not ticket or ticket.id <= 0:
            raise ValueError("Ticket must have a valid ID")

        # Procurar o ticket no banco
        ticket_orm = self._session.query(TicketORM).filter(
            TicketORM.id == ticket.id
        ).first()

        if not ticket_orm:
            raise ValueError(f"Ticket with ID {ticket.id} not found")

        # Atualizar campos
        ticket_orm.title = ticket.title
        ticket_orm.description = ticket.description
        ticket_orm.status = ticket.status
        ticket_orm.priority = ticket.priority
        ticket_orm.category = ticket.category

        # Commit
        self._session.commit()
        self._session.refresh(ticket_orm)

        return self._orm_to_domain(ticket_orm)

    def add_comment(self, comment: Comment) -> Comment:
        """
        Adiciona um comentário a um ticket.

        Guard Clauses verificam que tudo é válido.

        Args:
            comment: Comment sem ID

        Returns:
            Comment com ID atribuído

        Raises:
            ValueError: se comentário ou ticket são inválidos
        """
        # Guard Clauses
        if not comment:
            raise ValueError("Comment cannot be None")

        # Verificar que o ticket existe
        ticket_exists = self._session.query(TicketORM).filter(
            TicketORM.id == comment.ticket_id
        ).first()

        if not ticket_exists:
            raise ValueError(f"Ticket with ID {comment.ticket_id} not found")

        # Criar ORM e guardar
        comment_orm = CommentORM(
            ticket_id=comment.ticket_id,
            content=comment.content,
        )

        self._session.add(comment_orm)
        self._session.commit()
        self._session.refresh(comment_orm)

        return self._orm_to_domain_comment(comment_orm)

    # ========== Métodos privados para conversão ==========

    def _orm_to_domain(self, ticket_orm: TicketORM) -> Ticket:
        """
        Converte TicketORM (banco) para Ticket (domínio).

        Este é um exemplo de padrão converter/adapter.
        Centraliza a lógica de conversão num só lugar.

        Args:
            ticket_orm: instância de TicketORM do SQLAlchemy

        Returns:
            Instância de Ticket do domínio
        """
        return Ticket(
            id=ticket_orm.id,
            title=ticket_orm.title,
            description=ticket_orm.description,
            status=ticket_orm.status,
            priority=ticket_orm.priority,
            category=ticket_orm.category,
            created_at=ticket_orm.created_at,
            comments=[
                self._orm_to_domain_comment(comment_orm)
                for comment_orm in ticket_orm.comments
            ],
        )

    def _orm_to_domain_comment(self, comment_orm: CommentORM) -> Comment:
        """
        Converte CommentORM (banco) para Comment (domínio).

        Args:
            comment_orm: instância de CommentORM do SQLAlchemy

        Returns:
            Instância de Comment do domínio
        """
        return Comment(
            id=comment_orm.id,
            ticket_id=comment_orm.ticket_id,
            content=comment_orm.content,
            created_at=comment_orm.created_at,
        )
