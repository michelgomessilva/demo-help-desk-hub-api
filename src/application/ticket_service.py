"""
Serviço de Tickets - camada de lógica de negócio.

O service é o coração da aplicação. Aqui fica toda a lógica que não é
técnica nem específica de HTTP ou banco de dados.

Características importantes:
- Não importa nada de FastAPI ou HTTP
- Levanta exceções de domínio (TicketNotFoundError), não HTTP
- Depende só da interface ITicketRepository, não de implementações
- Qualquer mudança à forma como guardamos dados (memória -> banco) só afeta
  a injeção de dependência em ticket_routes.py, não aqui

Por que separar isto da API?
- Reutilização: podíamos ter CLI, scripts, webhooks que usam o mesmo serviço
- Testabilidade: mockar o repositório é trivial
- Clareza: a lógica de negócio está separada de detalhes técnicos
"""

from src.domain.tickets.repositories import ITicketRepository
from src.domain.tickets.models import Ticket, Comment
from src.domain.tickets.exceptions import TicketNotFoundError
from src.domain.tickets.enums import TicketStatus, TicketPriority, TicketCategory
from src.infrastructure.logging_config import get_logger
import math

# 👈 Obter logger estruturado
logger = get_logger(__name__)


class TicketService:
    """
    Serviço que coordena operações com tickets.

    Atributos privados:
        _repository: instância do repositório injetado no construtor

    Este é um exemplo de:
    - Injeção de Dependência: o repositório é passado no __init__
    - Segregação de Interface: usamos ITicketRepository, não uma classe específica
    - Princípio da Responsabilidade Única: só fazemos lógica de negócio
    """

    def __init__(self, repository: ITicketRepository):
        """
        Construtor com injeção de dependência.

        Argumentos:
            repository: implementação de ITicketRepository
                       (pode ser InMemory, SQLAlchemy, etc.)

        Por que injetar o repositório?
        - Separação de conceitos: o service não cria o repositório
        - Flexibilidade: ao testar, injetamos um mock
        - Não há acoplamento a uma implementação específica
        """
        self._repository = repository

    def create_ticket(
        self,
        title: str,
        description: str,
        priority: TicketPriority = TicketPriority.MEDIUM,
        category: TicketCategory = TicketCategory.SOFTWARE,
    ) -> Ticket:
        """
        Cria um novo ticket.

        Guard Clause: validações básicas no início.

        Argumentos:
            title: título do ticket
            description: descrição do problema
            priority: urgência (padrão: MEDIUM)
            category: tipo de problema (padrão: SOFTWARE)

        Retorna:
            O Ticket criado com ID atribuído
        """
        # 👈 Info: iniciar criação de ticket
        logger.info(
            "ticket_creation_started",
            title=title,
            category=category.value,
            priority=priority.value
        )

        # Guard Clauses: rejeitar dados inválidos cedo
        if not title or not title.strip():
            logger.warning("ticket_creation_failed", reason="empty_title")
            raise ValueError("Title cannot be empty")

        if not description or not description.strip():
            logger.warning("ticket_creation_failed", reason="empty_description")
            raise ValueError("Description cannot be empty")

        logger.debug("ticket_validation_passed", title=title, description_length=len(description))

        # Criar o modelo de domínio
        ticket = Ticket(
            id=0,  # O repositório atribui o ID real
            title=title,
            description=description,
            priority=priority,
            category=category,
        )

        # Guardar usando o repositório (não sabemos como)
        try:
            logger.debug("saving_ticket_to_repository", title=title)
            created_ticket = self._repository.create(ticket)
            logger.info("ticket_created_successfully", ticket_id=created_ticket.id, title=title)
            return created_ticket
        except Exception as e:
            logger.error(
                "ticket_creation_database_error",
                title=title,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    def list_tickets(
        self,
        status: TicketStatus | None = None,
        priority: TicketPriority | None = None,
        category: TicketCategory | None = None,
        page: int = 1,
        size: int = 10,
    ) -> tuple[list[Ticket], int]:
        """
        Lista todos os tickets com filtros opcionais e paginação.

        Guard Clauses: validar os parâmetros de paginação.

        Argumentos:
            status: filtrar por estado (None = sem filtro)
            priority: filtrar por prioridade (None = sem filtro)
            category: filtrar por categoria (None = sem filtro)
            page: número da página (começa em 1)
            size: items por página

        Retorna:
            tuple (tickets da página, total de tickets)
        """
        # 👈 Debug: iniciar listagem
        logger.debug(
            "listing_tickets_started",
            page=page,
            size=size,
            filters={"status": status.value if status else None, "priority": priority.value if priority else None, "category": category.value if category else None}
        )

        # Guard Clauses: paginação válida
        original_page = page
        original_size = size

        if page < 1:
            page = 1
            logger.debug("pagination_adjusted", field="page", original=original_page, adjusted=page)

        if size < 1 or size > 100:
            logger.warning("pagination_out_of_range", field="size", original=original_size, adjusted=size)
            size = 10

        try:
            # Pedir ao repositório
            tickets, total = self._repository.get_all(status, priority, category, page, size)
            logger.info(
                "tickets_listed_successfully",
                page=page,
                size=size,
                tickets_returned=len(tickets),
                total_tickets=total
            )
            return tickets, total
        except Exception as e:
            logger.error(
                "ticket_listing_error",
                page=page,
                size=size,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    def get_ticket(self, ticket_id: int) -> Ticket:
        """
        Obtém um ticket específico.

        Guard Clause: se não existe, lançar exceção de negócio (não HTTP).

        Argumentos:
            ticket_id: ID do ticket

        Retorna:
            O Ticket encontrado

        Lança:
            TicketNotFoundError: se o ticket não existe
        """
        # 👈 Debug: iniciar busca
        logger.debug("retrieving_ticket", ticket_id=ticket_id)

        try:
            ticket = self._repository.get_by_id(ticket_id)

            # Guard Clause: rejeitar cedo
            if not ticket:
                logger.warning("ticket_not_found", ticket_id=ticket_id)
                raise TicketNotFoundError(ticket_id)

            logger.info("ticket_retrieved_successfully", ticket_id=ticket_id, title=ticket.title, status=ticket.status.value)
            return ticket
        except TicketNotFoundError:
            raise
        except Exception as e:
            logger.error(
                "ticket_retrieval_error",
                ticket_id=ticket_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    def update_ticket(
        self,
        ticket_id: int,
        status: TicketStatus | None = None,
        priority: TicketPriority | None = None,
    ) -> Ticket:
        """
        Atualiza um ticket existente.

        Permite atualizar parcialmente: só o status, só a prioridade, ou ambos.

        Argumentos:
            ticket_id: ID do ticket a atualizar
            status: novo estado (None = não mudar)
            priority: nova prioridade (None = não mudar)

        Retorna:
            O Ticket atualizado

        Lança:
            TicketNotFoundError: se o ticket não existe
        """
        # 👈 Info: iniciar atualização
        logger.info(
            "ticket_update_started",
            ticket_id=ticket_id,
            updating_status=status is not None,
            updating_priority=priority is not None
        )

        try:
            # Guard Clause: obter o ticket (lança se não existe)
            ticket = self.get_ticket(ticket_id)

            # Atualizar apenas os campos que foram fornecidos
            old_status = ticket.status.value if ticket.status else None
            old_priority = ticket.priority.value if ticket.priority else None

            if status is not None:
                logger.debug("updating_ticket_status", ticket_id=ticket_id, old_status=old_status, new_status=status.value)
                ticket.status = status

            if priority is not None:
                logger.debug("updating_ticket_priority", ticket_id=ticket_id, old_priority=old_priority, new_priority=priority.value)
                ticket.priority = priority

            # Guardar
            logger.debug("saving_updated_ticket", ticket_id=ticket_id)
            updated_ticket = self._repository.update(ticket)

            logger.info(
                "ticket_updated_successfully",
                ticket_id=ticket_id,
                status_changed=(old_status != (status.value if status else old_status)),
                priority_changed=(old_priority != (priority.value if priority else old_priority))
            )
            return updated_ticket
        except Exception as e:
            logger.error(
                "ticket_update_error",
                ticket_id=ticket_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    def add_comment(self, ticket_id: int, content: str) -> Comment:
        """
        Adiciona um comentário a um ticket.

        Guard Clauses:
        - O ticket deve existir
        - O comentário deve ter conteúdo

        Argumentos:
            ticket_id: ID do ticket
            content: texto do comentário

        Retorna:
            O Comment criado com ID atribuído

        Lança:
            TicketNotFoundError: se o ticket não existe
            ValueError: se o conteúdo está vazio
        """
        # 👈 Info: iniciar adição de comentário
        logger.info("comment_addition_started", ticket_id=ticket_id, content_length=len(content))

        # Guard Clauses: validações no início
        if not content or not content.strip():
            logger.warning("comment_addition_failed", ticket_id=ticket_id, reason="empty_content")
            raise ValueError("Comment content cannot be empty")

        logger.debug("comment_validation_passed", ticket_id=ticket_id)

        try:
            # Garantir que o ticket existe
            # (se não existir, lança TicketNotFoundError)
            logger.debug("verifying_ticket_exists", ticket_id=ticket_id)
            self.get_ticket(ticket_id)

            # Criar o comentário
            logger.debug("creating_comment_object", ticket_id=ticket_id)
            comment = Comment(
                id=0,  # O repositório atribui o ID real
                ticket_id=ticket_id,
                content=content,
            )

            # Guardar usando o repositório
            logger.debug("saving_comment_to_repository", ticket_id=ticket_id)
            created_comment = self._repository.add_comment(comment)

            logger.info("comment_added_successfully", comment_id=created_comment.id, ticket_id=ticket_id)
            return created_comment
        except Exception as e:
            logger.error(
                "comment_addition_error",
                ticket_id=ticket_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
