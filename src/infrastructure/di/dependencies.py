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
from sqlalchemy.orm import Session
from src.application.ticket_service import TicketService
from src.domain.tickets.repositories import ITicketRepository
from src.infrastructure.database import get_db_session
from src.infrastructure.repositories.sqlalchemy_ticket_repository import (
    SQLAlchemyTicketRepository,
)
from src.infrastructure.logging_config import get_logger

# 👈 Obter logger estruturado
logger = get_logger(__name__)


def get_repository(db: Session = Depends(get_db_session)) -> ITicketRepository:
    """
    Dependência que fornece o repositório de tickets.

    FastAPI chama esta função automaticamente e injeta o resultado
    em qualquer rota que pedir 'repository: ITicketRepository = Depends(get_repository)'.

    Usa SQLAlchemyTicketRepository (PostgreSQL): os tickets ficam persistidos
    entre pedidos. A sessão da BD é injetada via Depends(get_db_session) e
    fechada automaticamente no fim do request.

    Returns:
        ITicketRepository: implementação do repositório (PostgreSQL)
    """
    logger.debug("repository_injection_requested", repository_type="SQLAlchemyTicketRepository")
    repository = SQLAlchemyTicketRepository(db)
    logger.debug("repository_injected", repository_type=type(repository).__name__)
    return repository


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
    logger.debug("service_injection_requested", repository_type=type(repository).__name__)
    service = TicketService(repository)
    logger.debug("service_injected", service_type=type(service).__name__)
    return service
