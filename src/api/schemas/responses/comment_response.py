"""
Schema de resposta para Comentários.

Define como um Comment é representado quando retornado pela API.
Cada entidade tem o seu próprio schema para manter separação de conceitos.
"""

from pydantic import BaseModel
from datetime import datetime


class CommentResponse(BaseModel):
    """
    Representação de um Comment como retornado pela API.

    Atributos:
        id: identificador único do comentário
        ticket_id: ID do ticket ao qual pertence
        content: texto do comentário
        created_at: quando foi criado
    """

    id: int
    ticket_id: int
    content: str
    created_at: datetime

    class Config:
        """Pydantic configuration para compatibilidade com ORM."""
        from_attributes = True
