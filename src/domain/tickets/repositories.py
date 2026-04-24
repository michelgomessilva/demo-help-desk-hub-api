"""
Interface abstrata para o repositório de Tickets.

O repositório é responsável por guardar e recuperar tickets. Tem uma interface
(este ficheiro) que define o contrato, e múltiplas implementações na camada
infrastructure (memória, banco de dados, etc.).

Por que a interface fica no domain?
- O domínio define o que precisa (contrato)
- A infraestrutura implementa o como
- O service depende só da interface, não da implementação específica
- Isto permite trocar implementações sem tocar no código de negócio

Este é o padrão SOLID:
- DIP (Dependency Inversion Principle): o service depende de uma abstração
- LSP (Liskov Substitution Principle): qualquer implementação pode substituir outra
"""

from abc import ABC, abstractmethod
from .models import Ticket, Comment
from .enums import TicketStatus, TicketPriority, TicketCategory


class ITicketRepository(ABC):
    """
    Interface que qualquer repositório de tickets deve implementar.

    Qualquer classe que implemente esta interface pode ser usada pelo service
    sem que o service saiba ou importe de detalhes de como os dados são guardados.
    """

    @abstractmethod
    def create(self, ticket: Ticket) -> Ticket:
        """
        Cria um novo ticket.

        Args:
            ticket: o ticket a guardar (sem ID atribuído ainda)

        Returns:
            o ticket criado com ID atribuído
        """
        pass

    @abstractmethod
    def get_all(
        self,
        status: TicketStatus | None,
        priority: TicketPriority | None,
        category: TicketCategory | None,
        page: int,
        size: int,
    ) -> tuple[list[Ticket], int]:
        """
        Lista todos os tickets com filtros opcionais e paginação.

        Nota importante: retorna um tuple com (items, total).
        O 'total' é o número TOTAL de registos que correspondem aos filtros,
        sem levar em conta a paginação. Isto permite ao cliente saber quantas
        páginas existem no total.

        Args:
            status: filtrar por estado (None = sem filtro)
            priority: filtrar por prioridade (None = sem filtro)
            category: filtrar por categoria (None = sem filtro)
            page: número da página (começa em 1)
            size: quantos items por página

        Returns:
            tuple contendo:
            - lista de tickets para a página pedida
            - total de tickets que correspondem aos filtros (sem paginação)
        """
        pass

    @abstractmethod
    def get_by_id(self, ticket_id: int) -> Ticket | None:
        """
        Obtém um ticket pelo seu ID.

        Args:
            ticket_id: o ID do ticket

        Returns:
            o ticket, ou None se não for encontrado
        """
        pass

    @abstractmethod
    def update(self, ticket: Ticket) -> Ticket:
        """
        Atualiza um ticket existente.

        Args:
            ticket: o ticket com os dados atualizados (deve ter um ID válido)

        Returns:
            o ticket atualizado
        """
        pass

    @abstractmethod
    def add_comment(self, comment: Comment) -> Comment:
        """
        Adiciona um comentário a um ticket.

        Args:
            comment: o comentário a adicionar (sem ID atribuído ainda)

        Returns:
            o comentário com ID atribuído
        """
        pass
