"""
Injeção de dependências (DI) para o FastAPI.

Este ficheiro centraliza todas as dependências do FastAPI em um único lugar.
As rotas importam daqui em vez de definir as dependências internamente.

Por que está na Infrastructure?
- Infrastructure = detalhes técnicos (FastAPI, SQLAlchemy, etc.)
- API = apenas HTTP (rotas + schemas)
- Mantém cada camada com sua responsabilidade clara
- Fácil trocar DI sem mexer na API

Por que separar?
- SRP (Single Responsibility Principle): cada ficheiro tem um propósito
- Manutenção fácil: trocar repositório apenas aqui
- Reutilização: múltiplas rotas usam a mesma injeção
- Testes: injetar mocks sem mexer nas rotas

Fluxo de injeção:
1. FastAPI chama get_repository() → retorna ITicketRepository
2. FastAPI chama get_service(repository) → retorna TicketService
3. FastAPI chama a rota com service injetado

SEMANA 4 - TROCAR REPOSITÓRIO:
Para usar PostgreSQL, alterar apenas a função get_repository() aqui.
Nenhuma outra mudança necessária em nenhum outro ficheiro!
"""

from fastapi import Depends
from src.application.ticket_service import TicketService
from src.domain.tickets.repositories import ITicketRepository
#from src.infrastructure.repositories.in_memory_ticket_repository import (
#    InMemoryTicketRepository,
#)
from src.infrastructure.database import SessionLocal
from src.infrastructure.repositories.sqlalchemy_ticket_repository import SQLAlchemyTicketRepository

def get_repository() -> ITicketRepository:
    """
    Dependência que fornece o repositório de tickets.

    FastAPI chama esta função automaticamente e injeta o resultado
    em qualquer rota que pedir 'repository: ITicketRepository = Depends(get_repository)'.

    Semana 2/3: retorna InMemoryTicketRepository
    Semana 4: muda para retornar SQLAlchemyTicketRepository

    Returns:
        ITicketRepository: implementação do repositório (memória ou BD)
    """
    #return InMemoryTicketRepository()
    return SQLAlchemyTicketRepository(SessionLocal())


def get_service(repository: ITicketRepository = Depends(get_repository)) -> TicketService:
    """
    Dependência que fornece o serviço de tickets.

    FastAPI injeta o repositório automaticamente via Depends(get_repository).
    Isto permite trocar a implementação do repositório sem mexer nas rotas.

    Args:
        repository: injetado automaticamente por FastAPI via get_repository()

    Returns:
        TicketService: serviço configurado com o repositório
    """
    return TicketService(repository)
