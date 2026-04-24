"""
Rotas HTTP para operações com Categorias.

Categorias é uma entidade simples: apenas retorna a lista de valores válidos.
Não há CRUD completo porque as categorias são pré-definidas nos enums.

Este é um exemplo de como manter as rotas simples quando a lógica também é simples.
"""

from fastapi import APIRouter
from src.domain.tickets.enums import TicketCategory

# Criar o router para estas rotas
router = APIRouter(tags=["Categories"])


@router.get("/categories")
def list_categories() -> list[str]:
    """
    Lista todas as categorias válidas para tickets.

    Endpoint:
        GET /categories

    Retorna:
        Lista de strings com os valores válidos das categorias.
        Exemplo: ["access", "hardware", "software", "network"]

    Por que retornar isto?
    - Permite ao cliente saber quais categorias são válidas
    - Evita enviar uma categoria inválida
    - Mantém a API auto-documentada
    """
    return [category.value for category in TicketCategory]
