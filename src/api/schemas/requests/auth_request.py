"""
Pydantic schemas for authentication requests.

Responsável por validação de entrada dos endpoints.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """
    Dados para cadastro com validações reforçadas.

    Validações:
    - name: 2-255 caracteres, apenas letras e espaços
    - email: Email válido (RFC 5322)
    - password: Mínimo 8 caracteres, complexidade obrigatória
    """

    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        pattern=r"^[a-zA-ZáéíóúãõçÀÁÂÃÄÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜàáâãäèéêëìíîïòóôõöùúûü\s]+$",
        description="Nome do usuário (apenas letras, acentos e espaços)"
    )

    email: EmailStr = Field(
        ...,
        description="Email válido e único"
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=1000,
        description="Senha com complexidade obrigatória"
    )

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        """
        Validar força da senha.

        Obrigatório:
        - Maiúscula
        - Minúscula
        - Número
        - Caractere especial (!@#$%^&*)
        """
        if not any(c.isupper() for c in v):
            raise ValueError('Senha deve conter maiúscula (A-Z)')

        if not any(c.islower() for c in v):
            raise ValueError('Senha deve conter minúscula (a-z)')

        if not any(c.isdigit() for c in v):
            raise ValueError('Senha deve conter número (0-9)')

        if not any(c in "!@#$%^&*" for c in v):
            raise ValueError('Senha deve conter caractere especial (!@#$%^&*)')

        return v

    @field_validator('name')
    @classmethod
    def validate_name_safe(cls, v):
        """
        Evitar injeção SQL via name.

        Bloquear palavras-chave suspeitas.
        """
        dangerous_keywords = ["drop", "delete", "insert", "select", "update", "execute"]

        if any(keyword in v.lower() for keyword in dangerous_keywords):
            raise ValueError('Nome contém palavras suspeitas')

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "João Silva",
                "email": "joao@email.com",
                "password": "MySecurePass123!"
            }
        }


class LoginRequest(BaseModel):
    """
    Dados para login.

    Validações:
    - email: Email válido
    - password: Senha
    """

    email: EmailStr = Field(
        ...,
        description="Email do usuário"
    )

    password: str = Field(
        ...,
        description="Senha do usuário"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "email": "joao@email.com",
                "password": "MySecurePass123!"
            }
        }
