"""
Rotas HTTP para operações com Tickets.

Esta camada é responsável por:
1. Receber requisições HTTP (query params, body JSON, etc.)
2. Validar entrada com Pydantic schemas
3. Chamar o service (lógica de negócio)
4. Capturar exceções de negócio e converter em HTTP (ex: 404)
5. Retornar resposta JSON com status code apropriado

Por que separar isto do service?
- O service nunca sabe de HTTP - pode ser reutilizado em CLI, scripts, etc.
- As exceções de negócio (TicketNotFoundError) são conceitos que o service
  conhece. As rotas as convertem em status codes HTTP (404, 400, etc.)
- Mantém cada camada com uma responsabilidade clara

Inversão de Controle: o service é injetado aqui (não criado dentro das funções).
Isto permite mockar o service em testes e trocar implementações facilmente.
"""

from fastapi import APIRouter, HTTPException, Depends, Security
from src.application.ticket_service import TicketService
from src.domain.tickets.exceptions import TicketNotFoundError
from src.domain.tickets.enums import TicketStatus, TicketPriority, TicketCategory
from src.infrastructure.di.dependencies import get_service
from src.infrastructure.di.auth_dependencies import get_current_user
from src.infrastructure.models.user_orm import UserORM
from src.api.schemas.requests.ticket_request import (
    CreateTicketRequest,
    UpdateTicketRequest,
    CreateCommentRequest,
)
from src.api.schemas.responses.ticket_response import TicketResponse
from src.api.schemas.responses.comment_response import CommentResponse
from src.api.schemas.responses.paginated_response import PaginatedResponse
from src.infrastructure.logging_config import get_logger

# 👈 Obter logger estruturado
logger = get_logger(__name__)

# Criar o router para estas rotas
router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("/", response_model=TicketResponse, status_code=201)
def create_ticket(
    request: CreateTicketRequest,
    service: TicketService = Depends(get_service),
    current_user: UserORM = Security(get_current_user),
) -> TicketResponse:
    """
    Criar um novo ticket.

    Recebe dados via JSON no body, valida com Pydantic (CreateTicketRequest),
    passa ao service, e retorna o ticket criado.

    Endpoint:
        POST /tickets

    Body exemplo:
        {
            "title": "Não consigo fazer login",
            "description": "A palavra-passe está correcta mas não entra",
            "priority": "high",
            "category": "access"
        }

    Retorna:
        TicketResponse (status 201 Created)
    """
    # 👈 Info: iniciar criação de ticket via endpoint
    logger.info(
        "create_ticket_endpoint_called",
        user_id=current_user.id,
        title=request.title,
        category=request.category.value
    )

    try:
        # 👈 Debug: chamar serviço
        logger.debug("calling_service_create_ticket", user_id=current_user.id)
        ticket = service.create_ticket(
            title=request.title,
            description=request.description,
            priority=request.priority,
            category=request.category,
        )

        # 👈 Info: ticket criado com sucesso
        logger.info(
            "ticket_created_via_endpoint",
            ticket_id=ticket.id,
            user_id=current_user.id,
            title=request.title
        )
        return ticket
    except ValueError as e:
        logger.warning(
            "create_ticket_validation_error",
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "create_ticket_endpoint_error",
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise


@router.get("/", response_model=PaginatedResponse[TicketResponse])
def list_tickets(
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
    category: TicketCategory | None = None,
    page: int = 1,
    size: int = 10,
    service: TicketService = Depends(get_service),
    current_user: UserORM = Security(get_current_user),
) -> PaginatedResponse[TicketResponse]:
    """
    Listar tickets com filtros opcionais e paginação.

    Endpoint:
        GET /tickets
        GET /tickets?status=open&priority=high
        GET /tickets?page=2&size=20

    Query params:
        status: OPEN, IN_PROGRESS, RESOLVED, CLOSED (opcional)
        priority: LOW, MEDIUM, HIGH, URGENT (opcional)
        category: ACCESS, HARDWARE, SOFTWARE, NETWORK (opcional)
        page: número da página (padrão: 1)
        size: items por página (padrão: 10)

    Retorna:
        PaginatedResponse contendo:
        - items: lista de TicketResponse
        - total: número total de tickets (todas as páginas)
        - page: página atual
        - size: items por página
        - pages: número total de páginas
    """
    # 👈 Info: iniciar listagem via endpoint
    logger.info(
        "list_tickets_endpoint_called",
        user_id=current_user.id,
        page=page,
        size=size,
        has_filters=any([status, priority, category])
    )

    try:
        # 👈 Debug: chamar serviço
        logger.debug("calling_service_list_tickets", user_id=current_user.id, page=page)
        tickets, total = service.list_tickets(
            status=status,
            priority=priority,
            category=category,
            page=page,
            size=size,
        )

        # 👈 Info: tickets listados com sucesso
        logger.info(
            "tickets_listed_via_endpoint",
            user_id=current_user.id,
            page=page,
            tickets_returned=len(tickets),
            total_tickets=total
        )

        # Usar o factory method para calcular 'pages' automaticamente
        return PaginatedResponse.from_data(
            items=tickets,
            total=total,
            page=page,
            size=size,
        )
    except Exception as e:
        logger.error(
            "list_tickets_endpoint_error",
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: int,
    service: TicketService = Depends(get_service),
    current_user: UserORM = Security(get_current_user),
) -> TicketResponse:
    """
    Obter um ticket específico pelo ID.

    Endpoint:
        GET /tickets/5

    Parâmetros:
        ticket_id: ID do ticket (path parameter)

    Retorna:
        TicketResponse (status 200 OK)

    Lança:
        404 Not Found: se o ticket não existe
    """
    # 👈 Debug: iniciar busca de ticket
    logger.debug("get_ticket_endpoint_called", user_id=current_user.id, ticket_id=ticket_id)

    try:
        # 👈 Debug: chamar serviço
        logger.debug("calling_service_get_ticket", ticket_id=ticket_id)
        ticket = service.get_ticket(ticket_id)

        # 👈 Info: ticket encontrado
        logger.info("ticket_retrieved_via_endpoint", user_id=current_user.id, ticket_id=ticket_id)
        return ticket
    except TicketNotFoundError as e:
        # 👈 Warning: ticket não encontrado
        logger.warning("ticket_not_found_via_endpoint", user_id=current_user.id, ticket_id=ticket_id)
        # Converter exceção de negócio em HTTP 404
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(
            "get_ticket_endpoint_error",
            user_id=current_user.id,
            ticket_id=ticket_id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: int,
    request: UpdateTicketRequest,
    service: TicketService = Depends(get_service),
    current_user: UserORM = Security(get_current_user),
) -> TicketResponse:
    """
    Atualizar um ticket existente.

    Permite atualizar parcialmente: só o status, só a prioridade, ou ambos.
    Campos não fornecidos não são alterados.

    Endpoint:
        PATCH /tickets/5

    Body exemplo:
        {
            "status": "in_progress"
        }

    ou:

        {
            "status": "resolved",
            "priority": "low"
        }

    Parâmetros:
        ticket_id: ID do ticket (path parameter)

    Retorna:
        TicketResponse (status 200 OK)

    Lança:
        404 Not Found: se o ticket não existe
    """
    # 👈 Info: iniciar atualização via endpoint
    logger.info(
        "update_ticket_endpoint_called",
        user_id=current_user.id,
        ticket_id=ticket_id,
        updating_status=request.status is not None,
        updating_priority=request.priority is not None
    )

    try:
        # 👈 Debug: chamar serviço
        logger.debug("calling_service_update_ticket", ticket_id=ticket_id, user_id=current_user.id)
        updated_ticket = service.update_ticket(
            ticket_id=ticket_id,
            status=request.status,
            priority=request.priority,
        )

        # 👈 Info: ticket atualizado com sucesso
        logger.info("ticket_updated_via_endpoint", user_id=current_user.id, ticket_id=ticket_id)
        return updated_ticket
    except TicketNotFoundError as e:
        # 👈 Warning: ticket não encontrado
        logger.warning("update_ticket_not_found", user_id=current_user.id, ticket_id=ticket_id)
        # Converter exceção de negócio em HTTP 404
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(
            "update_ticket_endpoint_error",
            user_id=current_user.id,
            ticket_id=ticket_id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise


@router.post("/{ticket_id}/comments", response_model=CommentResponse, status_code=201)
def add_comment(
    ticket_id: int,
    request: CreateCommentRequest,
    service: TicketService = Depends(get_service),
    current_user: UserORM = Security(get_current_user),
) -> CommentResponse:
    """
    Adicionar um comentário a um ticket.

    Endpoint:
        POST /tickets/5/comments

    Body:
        {
            "content": "Consegui resolver! Era um cookie antigo."
        }

    Parâmetros:
        ticket_id: ID do ticket (path parameter)

    Retorna:
        CommentResponse (status 201 Created)

    Lança:
        404 Not Found: se o ticket não existe
        400 Bad Request: se o conteúdo está vazio
    """
    # 👈 Info: iniciar adição de comentário via endpoint
    logger.info(
        "add_comment_endpoint_called",
        user_id=current_user.id,
        ticket_id=ticket_id,
        content_length=len(request.content)
    )

    try:
        # 👈 Debug: chamar serviço
        logger.debug("calling_service_add_comment", ticket_id=ticket_id, user_id=current_user.id)
        comment = service.add_comment(
            ticket_id=ticket_id,
            content=request.content,
        )

        # 👈 Info: comentário adicionado com sucesso
        logger.info("comment_added_via_endpoint", user_id=current_user.id, ticket_id=ticket_id, comment_id=comment.id)
        return comment
    except TicketNotFoundError as e:
        # 👈 Warning: ticket não encontrado
        logger.warning("add_comment_ticket_not_found", user_id=current_user.id, ticket_id=ticket_id)
        # Converter exceção de negócio em HTTP 404
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        # 👈 Warning: conteúdo inválido
        logger.warning("add_comment_validation_error", user_id=current_user.id, ticket_id=ticket_id, error=str(e))
        # Converter exceção de validação em HTTP 400
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "add_comment_endpoint_error",
            user_id=current_user.id,
            ticket_id=ticket_id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise
