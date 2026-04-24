"""
Schema genérico de resposta paginada.

Este schema é reutilizável para qualquer entidade (Tickets, Comments, etc.).
Usa Generic[T] do Python para aceitar qualquer tipo T.

Por que genérico?
- DRY Principle: em vez de criar PaginatedTicketsResponse, PaginatedCommentsResponse,
  etc., temos um único schema que funciona para todos
- Legibilidade: a intenção é clara - isto é uma resposta paginada de algo
- Facilidade: adicionar uma nova entidade não requer criar um novo schema de paginação
"""

from typing import Generic, TypeVar
from pydantic import BaseModel
import math

# T é um tipo genérico - pode ser TicketResponse, CommentResponse, etc.
T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Resposta paginada que funciona com qualquer tipo T.

    Exemplo de uso:
        @router.get("/")
        def list_tickets() -> PaginatedResponse[TicketResponse]:
            ...

    Atributos:
        items: lista dos items da página atual
        total: número TOTAL de items (sem levar em conta paginação)
        page: número da página atual (começa em 1)
        size: quantos items por página
        pages: número total de páginas (calculado de total e size)

    Por que retornar 'pages'?
    - O cliente sabe de imediato quantas páginas existem
    - Não precisa fazer uma segunda chamada ou fazer contas
    - Facilita UI (botões "próxima página", "página X de Y")
    """

    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    class Config:
        """Pydantic configuration."""
        from_attributes = True

    @classmethod
    def from_data(cls, items: list[T], total: int, page: int, size: int) -> "PaginatedResponse[T]":
        """
        Factory method (método de conveniência) para criar uma resposta paginada.

        Calcula automaticamente o número de páginas usando math.ceil.

        Argumentos:
            items: lista de items para a página
            total: total de items (todas as páginas)
            page: número da página
            size: items por página

        Retorna:
            Uma instância de PaginatedResponse com 'pages' calculado
        """
        # Guard Clause: se size for 0, usar 1 para evitar divisão por zero
        if size <= 0:
            size = 1

        pages = math.ceil(total / size)
        return cls(items=items, total=total, page=page, size=size, pages=pages)
