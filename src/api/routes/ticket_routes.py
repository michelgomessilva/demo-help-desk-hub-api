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


from sqlalchemy.orm import Session
from fastapi import APIRouter, HTTPException, Depends
from src.application.ticket_service import TicketService
from src.domain.tickets.exceptions import TicketNotFoundError
from src.domain.tickets.enums import TicketStatus, TicketPriority, TicketCategory
from src.infrastructure.di.dependencies import get_service
from src.api.schemas.requests.ticket_request import (
    CreateTicketRequest,
    UpdateTicketRequest,
    CreateCommentRequest,
)
from src.api.schemas.responses.ticket_response import TicketResponse
from src.api.schemas.responses.comment_response import CommentResponse
from src.api.schemas.responses.paginated_response import PaginatedResponse
from src.infrastructure.di.auth_dependencies import get_current_user, require_admin
from src.infrastructure.models.user_orm import UserORM
from src.infrastructure.models.ticket_orm import TicketORM
from src.infrastructure.database import get_db_session

# Criar o router para estas rotas
router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("/", response_model=TicketResponse, status_code=201)
def create_ticket(
    request: CreateTicketRequest,
    service: TicketService = Depends(get_service),
    current_user: UserORM = Depends(get_current_user)
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

    print(f"User {current_user.name} ({current_user.id}) listou tickets")

    ticket = service.create_ticket(
        title=request.title,
        description=request.description,
        priority=request.priority,
        category=request.category,
    )

    return ticket


@router.get("/", response_model=PaginatedResponse[TicketResponse])
def list_tickets(
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
    category: TicketCategory | None = None,
    page: int = 1,
    size: int = 10,
    service: TicketService = Depends(get_service),
    current_user: UserORM = Depends(get_current_user)
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

    print(f"User {current_user.name} ({current_user.id}) listou tickets")
    tickets, total = service.list_tickets(
        status=status,
        priority=priority,
        category=category,
        page=page,
        size=size,
    )

    # Usar o factory method para calcular 'pages' automaticamente
    return PaginatedResponse.from_data(
        items=tickets,
        total=total,
        page=page,
        size=size,
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: int,
    service: TicketService = Depends(get_service),
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
    try:
        return service.get_ticket(ticket_id)
    except TicketNotFoundError as e:
        # Converter exceção de negócio em HTTP 404
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: int,
    request: UpdateTicketRequest,
    service: TicketService = Depends(get_service),
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
    try:
        return service.update_ticket(
            ticket_id=ticket_id,
            status=request.status,
            priority=request.priority,
        )
    except TicketNotFoundError as e:
        # Converter exceção de negócio em HTTP 404
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{ticket_id}/comments", response_model=CommentResponse, status_code=201)
def add_comment(
    ticket_id: int,
    request: CreateCommentRequest,
    service: TicketService = Depends(get_service),
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
    try:
        return service.add_comment(
            ticket_id=ticket_id,
            content=request.content,
        )
    except TicketNotFoundError as e:
        # Converter exceção de negócio em HTTP 404
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        # Converter exceção de validação em HTTP 400
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/admin/all")
async def list_all_tickets_admin(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db_session),
    admin_user: UserORM = Depends(require_admin)  # 👈 ADMIN only!
):
    """
    Lista TODOS os tickets (apenas ADMIN).
    
    ✅ Apenas administradores!
    
    Args:
        admin_user: Injetado como UserORM com role == "ADMIN"
    """
    print(f"Admin {admin_user.name} ({admin_user.id}) acessou lista admin")
    
    tickets = db.query(TicketORM).offset(skip).limit(limit).all()
    return {"tickets": tickets, "admin": admin_user.name}


@router.delete("/{ticket_id}")
async def delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db_session),
    admin_user: UserORM = Depends(require_admin)  # 👈 ADMIN only!
):
    """
    Deletar ticket (apenas ADMIN).
    
    ✅ Apenas administradores!
    """
    ticket = db.query(TicketORM).filter(TicketORM.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    
    db.delete(ticket)
    db.commit()
    
    return {"message": f"Ticket {ticket_id} deletado por {admin_user.name}"}