"""
Modelos de domínio para Tickets e Comentários.

Estas classes representam as entidades puras do negócio, sem qualquer
dependência de HTTP ou banco de dados. São dataclasses simples que
encapsulam os dados e comportamentos do domínio.

Por que existem aqui e não em outro lugar?
- Ficam no domain porque representam o negócio, não detalhes técnicos
- Não herdam de ORM (SQLAlchemy) para manter separação de conceitos
- São reutilizadas por todas as camadas (service, API, repositório)
"""

from dataclasses import dataclass, field
from datetime import datetime
from .enums import TicketStatus, TicketPriority, TicketCategory


@dataclass
class Comment:
    """
    Representa um comentário num ticket.

    Um comentário é uma anotação feita por alguém sobre o estado ou progresso
    de um ticket. Tem um conteúdo, um dono (implícito por enquanto), e uma data.

    Atributos:
        id: identificador único do comentário
        ticket_id: a qual ticket pertence este comentário
        content: texto do comentário
        created_at: quando foi criado o comentário
    """
    id: int
    ticket_id: int
    content: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Ticket:
    """
    Representa um ticket (chamado de suporte técnico).

    Um ticket é um pedido de ajuda do utilizador. Pode ser aberto, estar
    em progresso, resolvido ou fechado. Tem uma prioridade e uma categoria.

    Atributos:
        id: identificador único
        title: título curto do problema
        description: descrição detalhada do que precisa de ser resolvido
        status: estado atual (aberto, em progresso, resolvido, fechado)
        priority: urgência (baixa, média, alta, urgente)
        category: tipo de problema (acesso, hardware, software, rede)
        created_at: quando foi criado
        comments: lista de comentários associados ao ticket
    """
    id: int
    title: str
    description: str
    status: TicketStatus = TicketStatus.OPEN
    priority: TicketPriority = TicketPriority.MEDIUM
    category: TicketCategory = TicketCategory.SOFTWARE
    created_at: datetime = field(default_factory=datetime.now)
    comments: list[Comment] = field(default_factory=list)
