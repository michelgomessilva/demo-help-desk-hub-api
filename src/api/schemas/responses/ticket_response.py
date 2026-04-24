"""
Schema de resposta para Tickets.

Este ficheiro define como um Ticket é representado quando retornado pela API.
Usa Pydantic para validação automática e documentação automática no Swagger.

Por que um ficheiro só para isto?
- Cada entidade (Ticket, Comment, etc.) tem a sua própria resposta
- Mantém os ficheiros pequenos e focados
- Facilita reutilização (este schema é usado em várias rotas)
- Segue o princípio SRP (Single Responsibility Principle)
"""

from pydantic import BaseModel
from datetime import datetime
from src.domain.tickets.enums import TicketStatus, TicketPriority, TicketCategory


class TicketResponse(BaseModel):
    """
    Representação de um Ticket como retornado pela API.

    Pydantic valida automaticamente que todos os campos estão presentes
    e têm o tipo correto. Também gera documentação automática no Swagger.

    Atributos (no JSON retornado):
        id: identificador único do ticket
        title: título do problema
        description: descrição detalhada
        status: estado atual
        priority: urgência
        category: tipo de problema
        created_at: quando foi criado
    """

    id: int
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    category: TicketCategory
    created_at: datetime

    class Config:
        """
        Configuração do Pydantic.

        from_attributes=True permite converter um modelo SQLAlchemy
        (Semana 4) para este schema automaticamente.
        """
        from_attributes = True
