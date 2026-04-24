"""
Schemas de request para operações com Tickets.

Estes schemas validam o que o cliente envia na requisição.
Pydantic rejeita automaticamente dados inválidos.

Por que ficam aqui?
- Definem o contrato de entrada da API
- Cada operação pode ter um schema diferente
  (CreateTicketRequest vs UpdateTicketRequest)
- Validação automática: o Pydantic garante que os dados estão corretos
  antes de o código de negócio os usar
"""

from pydantic import BaseModel, Field
from src.domain.tickets.enums import TicketStatus, TicketPriority, TicketCategory


class CreateTicketRequest(BaseModel):
    """
    Request para criar um novo ticket.

    Quem envia isto:
        POST /tickets
        {
            "title": "Não consigo fazer login",
            "description": "Tenho a palavra-passe mas a login não funciona",
            "priority": "high",
            "category": "access"
        }

    Atributos:
        title: obrigatório, descrição curta
        description: obrigatório, detalhes do problema
        priority: opcional, padrão é MEDIUM
        category: opcional, padrão é SOFTWARE
    """

    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)
    priority: TicketPriority = TicketPriority.MEDIUM
    category: TicketCategory = TicketCategory.SOFTWARE


class UpdateTicketRequest(BaseModel):
    """
    Request para atualizar um ticket existente.

    Quem envia isto:
        PATCH /tickets/5
        {
            "status": "in_progress",
            "priority": "low"
        }

    Nota: todos os campos são opcionais. Isto permite atualizar
    só o status, só a prioridade, ou ambos.

    Atributos:
        status: novo estado (opcional)
        priority: nova prioridade (opcional)
    """

    status: TicketStatus | None = None
    priority: TicketPriority | None = None


class CreateCommentRequest(BaseModel):
    """
    Request para adicionar um comentário a um ticket.

    Quem envia isto:
        POST /tickets/5/comments
        {
            "content": "Consegui resolver! Era um cookie antigo no browser."
        }

    Atributos:
        content: texto do comentário
    """

    content: str = Field(..., min_length=1, max_length=5000)
