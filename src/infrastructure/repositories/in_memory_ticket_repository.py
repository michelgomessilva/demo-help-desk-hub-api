"""
Implementação em memória do repositório de Tickets.

Esta implementação guarda todos os tickets num dicionário Python. É útil para:
- Desenvolvimento (não precisa de banco de dados configurado)
- Testes (dados não persistem entre execuções)
- Prototipagem rápida

Na Semana 4, trocaremos isto por uma implementação que usa PostgreSQL.
O serviço não muda nada porque depende só da interface ITicketRepository.

Por que guardar em memória?
- Demonstra que a lógica de negócio é separada de como os dados são guardados
- Permite aprender a arquitetura antes de complicar com bancos de dados
"""

from src.domain.tickets.repositories import ITicketRepository
from src.domain.tickets.models import Ticket, Comment
from src.domain.tickets.enums import TicketStatus, TicketPriority, TicketCategory
from src.infrastructure.logging_config import get_logger
import math

# 👈 Obter logger estruturado
logger = get_logger(__name__)


class InMemoryTicketRepository(ITicketRepository):
    """
    Repositório que armazena tickets em memória (num dicionário Python).

    Atributos privados (começam com _):
        _tickets: dicionário onde guardamos os tickets {id: Ticket}
        _comments: dicionário para comentários {id: Comment}
        _next_ticket_id: próximo ID a atribuir a um ticket
        _next_comment_id: próximo ID a atribuir a um comentário

    Por que usar atributos privados?
    - Encapsulamento: quem usa a classe não pode mexer nos dados diretamente
    - Segurança: garante que a classe mantém a integridade dos dados
    """

    def __init__(self):
        """Inicializa o repositório com estruturas vazias."""
        self._tickets: dict[int, Ticket] = {}
        self._comments: dict[int, Comment] = {}
        self._next_ticket_id = 1
        self._next_comment_id = 1

    def create(self, ticket: Ticket) -> Ticket:
        """
        Cria um novo ticket atribuindo-lhe um ID único.

        Guard Clause: verificamos que o ticket não é None no início.
        """
        if not ticket:
            logger.warning("ticket_creation_skipped", reason="ticket_is_none")
            raise ValueError("Ticket cannot be None")

        logger.debug("ticket_in_memory_create_started", title=ticket.title, category=ticket.category.value)

        # Atribuir um ID único
        ticket.id = self._next_ticket_id
        self._next_ticket_id += 1

        # Guardar no dicionário
        self._tickets[ticket.id] = ticket

        logger.info("ticket_created_in_memory", ticket_id=ticket.id, title=ticket.title, total_tickets=len(self._tickets))
        return ticket

    def get_all(
        self,
        status: TicketStatus | None = None,
        priority: TicketPriority | None = None,
        category: TicketCategory | None = None,
        page: int = 1,
        size: int = 10,
    ) -> tuple[list[Ticket], int]:
        """
        Lista tickets com filtros e paginação.

        Algoritmo:
        1. Começar com todos os tickets
        2. Filtrar por status (se provided)
        3. Filtrar por prioridade (se provided)
        4. Filtrar por categoria (se provided)
        5. Guardar o total (para saber quantas páginas há)
        6. Calcular skip e limit para a página pedida
        7. Retornar items + total

        Por que retornar o total?
        - O cliente precisa saber quantas páginas existem
        - Sem isto, teria de fazer uma segunda chamada só para contar

        Guard Clause: validar que page e size são válidos.
        """
        logger.debug("ticket_in_memory_get_all_started", page=page, size=size, has_filters=any([status, priority, category]))

        if page < 1:
            page = 1
        if size < 1:
            size = 10

        # Começar com todos os tickets
        results = list(self._tickets.values())

        # Aplicar filtros (Guard Clauses)
        if status:
            results = [t for t in results if t.status == status]
        if priority:
            results = [t for t in results if t.priority == priority]
        if category:
            results = [t for t in results if t.category == category]

        # Guardar o total ANTES de fazer paginação
        total = len(results)

        # Calcular skip e aplicar paginação
        skip = (page - 1) * size
        paged_results = results[skip : skip + size]

        logger.info("tickets_listed_in_memory", page=page, size=size, tickets_returned=len(paged_results), total_tickets=total)
        return (paged_results, total)

    def get_by_id(self, ticket_id: int) -> Ticket | None:
        """
        Obtém um ticket pelo seu ID.

        Guard Clause: se ticket_id não existe, retornar None imediatamente.
        """
        logger.debug("ticket_in_memory_get_by_id_started", ticket_id=ticket_id)
        ticket = self._tickets.get(ticket_id)

        if ticket:
            logger.debug("ticket_found_in_memory", ticket_id=ticket_id, title=ticket.title)
        else:
            logger.warning("ticket_not_found_in_memory", ticket_id=ticket_id)

        return ticket

    def update(self, ticket: Ticket) -> Ticket:
        """
        Atualiza um ticket existente.

        Guard Clauses:
        - Verificar que o ticket tem um ID válido
        - Verificar que o ticket existe
        """
        logger.info("ticket_in_memory_update_started", ticket_id=ticket.id if ticket else None)

        if not ticket or ticket.id <= 0:
            logger.warning("ticket_update_invalid_id", ticket_id=ticket.id if ticket else None)
            raise ValueError("Ticket must have a valid ID")

        if ticket.id not in self._tickets:
            logger.warning("ticket_not_found_for_update_in_memory", ticket_id=ticket.id)
            raise ValueError(f"Ticket with ID {ticket.id} not found")

        logger.debug("updating_ticket_in_memory", ticket_id=ticket.id, new_status=ticket.status.value)
        self._tickets[ticket.id] = ticket
        logger.info("ticket_updated_in_memory", ticket_id=ticket.id)
        return ticket

    def add_comment(self, comment: Comment) -> Comment:
        """
        Adiciona um comentário a um ticket.

        Guard Clauses:
        - Verificar que o ticket existe
        - Verificar que o comentário é válido
        """
        logger.info("comment_addition_in_memory_started", ticket_id=comment.ticket_id if comment else None)

        if not comment:
            logger.warning("comment_addition_skipped_in_memory", reason="comment_is_none")
            raise ValueError("Comment cannot be None")

        if comment.ticket_id not in self._tickets:
            logger.warning("comment_addition_failed_in_memory", ticket_id=comment.ticket_id, reason="ticket_not_found")
            raise ValueError(f"Ticket with ID {comment.ticket_id} not found")

        logger.debug("creating_comment_in_memory", ticket_id=comment.ticket_id)

        # Atribuir um ID único ao comentário
        comment.id = self._next_comment_id
        self._next_comment_id += 1

        # Guardar no dicionário global de comentários
        self._comments[comment.id] = comment

        # Adicionar também à lista de comentários do ticket
        ticket = self._tickets[comment.ticket_id]
        ticket.comments.append(comment)

        logger.info("comment_added_in_memory", comment_id=comment.id, ticket_id=comment.ticket_id)
        return comment
