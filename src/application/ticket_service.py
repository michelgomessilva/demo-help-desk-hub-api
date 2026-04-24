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
import math


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
        # Guard Clauses: rejeitar dados inválidos cedo
        if not title or not title.strip():
            raise ValueError("Title cannot be empty")
        if not description or not description.strip():
            raise ValueError("Description cannot be empty")

        # Criar o modelo de domínio
        ticket = Ticket(
            id=0,  # O repositório atribui o ID real
            title=title,
            description=description,
            priority=priority,
            category=category,
        )

        # Guardar usando o repositório (não sabemos como)
        return self._repository.create(ticket)

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
        # Guard Clauses: paginação válida
        if page < 1:
            page = 1
        if size < 1 or size > 100:
            size = 10

        # Pedir ao repositório
        return self._repository.get_all(status, priority, category, page, size)

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
        ticket = self._repository.get_by_id(ticket_id)

        # Guard Clause: rejeitar cedo
        if not ticket:
            raise TicketNotFoundError(ticket_id)

        return ticket

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
        # Guard Clause: obter o ticket (lança se não existe)
        ticket = self.get_ticket(ticket_id)

        # Atualizar apenas os campos que foram fornecidos
        if status is not None:
            ticket.status = status
        if priority is not None:
            ticket.priority = priority

        # Guardar
        return self._repository.update(ticket)

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
        # Guard Clauses: validações no início
        if not content or not content.strip():
            raise ValueError("Comment content cannot be empty")

        # Garantir que o ticket existe
        # (se não existir, lança TicketNotFoundError)
        self.get_ticket(ticket_id)

        # Criar o comentário
        comment = Comment(
            id=0,  # O repositório atribui o ID real
            ticket_id=ticket_id,
            content=content,
        )

        # Guardar usando o repositório
        return self._repository.add_comment(comment)
