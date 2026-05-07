"""
Pydantic schemas for authentication responses.

Responsável por formatar resposta de forma segura.
"""

from pydantic import BaseModel, Field
from datetime import datetime


class UserResponse(BaseModel):
    """
    Dados do usuário retornados (SEM senha!).

    ⚠️ NUNCA incluir password_hash na resposta!
    """

    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True  # 👈 Converter ORM → Pydantic


class TokenResponse(BaseModel):
    """
    Token JWT retornado após login bem-sucedido.

    Campos:
    - access_token: JWT assinado
    - token_type: Sempre "bearer" (OAuth2)
    - user: Dados do usuário (sem senha)
    """

    access_token: str = Field(
        ...,
        description="JWT token"
    )
    token_type: str = Field(
        default="bearer",
        description="Tipo de autenticação (OAuth2)"
    )
    user: UserResponse = Field(
        ...,
        description="Dados do usuário autenticado"
    )
