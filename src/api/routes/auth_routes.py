"""
Rotas de autenticação (register, login).

Endpoints:
- POST /auth/register : Criar novo usuário
- POST /auth/login    : Login e retornar token JWT
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from src.infrastructure.database import get_db_session
from src.application.auth_service import AuthService
from src.infrastructure.security.jwt_handler import create_access_token
from src.api.schemas.requests.auth_request import RegisterRequest, LoginRequest
from src.api.schemas.responses.auth_response import TokenResponse, UserResponse
from src.infrastructure.logging_config import get_logger

# 👈 Obter logger estruturado
logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db_session)
):
    """
    Endpoint: POST /auth/register

    Registrar novo usuário.

    Passos:
    1. Validar dados com Pydantic
    2. AuthService.register() - hash senha e salvar
    3. Retornar usuário criado (SEM senha)

    Request:
    {
        "name": "João Silva",
        "email": "joao@email.com",
        "password": "MySecurePass123!"
    }

    Response (201 Created):
    {
        "id": 1,
        "name": "João Silva",
        "email": "joao@email.com",
        "role": "USER",
        "is_active": true,
        "created_at": "2026-05-07T10:00:00"
    }
    """
    # 👈 Info: iniciar registro via endpoint
    client_ip = request.client.host if request.client else "unknown"
    logger.info(
        "register_endpoint_called",
        email=data.email,
        name=data.name,
        client_ip=client_ip
    )

    try:
        # 👈 Debug: chamar serviço
        logger.debug("calling_auth_service_register", email=data.email)
        auth_service = AuthService(db)
        user = auth_service.register(data.name, data.email, data.password)

        # 👈 Info: usuário registrado com sucesso
        logger.info(
            "user_registered_via_endpoint",
            user_id=user.id,
            email=data.email,
            client_ip=client_ip
        )
        return user
    except HTTPException as e:
        logger.warning(
            "register_validation_error",
            email=data.email,
            status_code=e.status_code,
            detail=e.detail,
            client_ip=client_ip
        )
        raise
    except Exception as e:
        logger.error(
            "register_endpoint_error",
            email=data.email,
            error=str(e),
            error_type=type(e).__name__,
            client_ip=client_ip
        )
        raise


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db_session)
):
    """
    Endpoint: POST /auth/login

    Login - retornar JWT token.

    Passos:
    1. AuthService.authenticate() - verificar email e senha
    2. Se OK: criar JWT
    3. Retornar token + dados do usuário

    Request:
    {
        "email": "joao@email.com",
        "password": "MySecurePass123!"
    }

    Response (200 OK):
    {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "token_type": "bearer",
        "user": { ... }
    }
    """
    # 👈 Info: iniciar login via endpoint
    client_ip = request.client.host if request.client else "unknown"
    logger.info(
        "login_endpoint_called",
        email=data.email,
        client_ip=client_ip
    )

    try:
        auth_service = AuthService(db)

        # 👈 Debug: autenticar
        logger.debug("authenticating_user", email=data.email)
        user = auth_service.authenticate(data.email, data.password)

        if not user:
            # 👈 Warning: credenciais inválidas
            logger.warning(
                "login_failed_invalid_credentials",
                email=data.email,
                client_ip=client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos"
            )

        # 👈 Debug: criar token JWT
        logger.debug("creating_jwt_token", user_id=user.id, email=data.email)
        token = create_access_token(user_id=user.id, role=user.role)

        # 👈 Info: login bem-sucedido
        logger.info(
            "login_successful",
            user_id=user.id,
            email=data.email,
            client_ip=client_ip,
            role=user.role
        )

        # ✅ Retornar token + dados do usuário
        return TokenResponse(
            access_token=token,
            user=UserResponse.model_validate(user)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "login_endpoint_error",
            email=data.email,
            error=str(e),
            error_type=type(e).__name__,
            client_ip=client_ip
        )
        raise
