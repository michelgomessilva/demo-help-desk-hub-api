"""
Dependências de autenticação para FastAPI.

FastAPI permite injectar dependências em endpoints.
Aqui criamos funções que:
1. Extraem o token do header Authorization
2. Validam o token com JWT
3. Retornam o usuário autenticado ou erro 401/403
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.infrastructure.database import get_db_session
from src.infrastructure.models.user_orm import UserORM
from src.infrastructure.security.jwt_handler import verify_token


# 👈 HTTPBearer extrai "Authorization: Bearer <token>"
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_session)
) -> UserORM:
    """
    Dependência: Extrair e validar JWT.

    Passos:
    1. Extrair token do header Authorization: Bearer <token>
    2. Verificar assinatura e expiração com verify_token()
    3. Buscar usuário no banco
    4. Retornar usuário ou erro 401

    Uso em endpoint:
    ```
    @router.get("/tickets")
    async def list_tickets(
        current_user: UserORM = Depends(get_current_user)  # 👈 Aqui
    ):
        print(f"Usuário: {current_user.name}")
        return tickets
    ```

    Args:
        credentials: HTTPAuthCredentials (token extraído automaticamente)
        db: Session do banco

    Returns:
        UserORM: Usuário autenticado

    Raises:
        HTTPException 401: Se token inválido/expirado
        HTTPException 401: Se usuário não existe
        HTTPException 403: Se usuário desativado
    """

    token = credentials.credentials

    # 👈 Verificar token
    decoded = verify_token(token)

    if decoded is None:
        # ❌ Token inválido ou expirado
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = decoded["user_id"]

    # 👈 Buscar usuário no banco (dados atualizados)
    user = db.query(UserORM).filter(UserORM.id == user_id).first()

    if not user:
        # ❌ Usuário não existe (foi deletado?)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não existe"
        )

    if not user.is_active:
        # ❌ Usuário foi desativado
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário desativado"
        )

    # ✅ Usuário válido e ativo
    return user


async def require_admin(
    current_user: UserORM = Depends(get_current_user)
) -> UserORM:
    """
    Dependência: Verificar se usuário é ADMIN.

    Passos:
    1. Já passou por get_current_user (autenticado)
    2. Verificar se role == "ADMIN"
    3. Se não, retornar 403 Forbidden

    Uso em endpoint:
    ```
    @router.delete("/{ticket_id}")
    async def delete_ticket(
        ticket_id: int,
        admin_user: UserORM = Depends(require_admin)  # 👈 ADMIN only!
    ):
        return {"message": f"Deletado por {admin_user.name}"}
    ```

    Args:
        current_user: UserORM (já autenticado)

    Returns:
        UserORM: Se role == "ADMIN"

    Raises:
        HTTPException 403: Se não for ADMIN
    """

    if current_user.role != "ADMIN":
        # ❌ Não é ADMIN
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem acessar este recurso"
        )

    # ✅ É ADMIN
    return current_user
