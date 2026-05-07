"""
Handler de JWT.

Responsável por:
- Gerar JWT (create_access_token)
- Verificar JWT (verify_token)
"""

import os
from datetime import datetime, timedelta
from jose import JWTError, jwt


# 👈 Carregar do .env
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


def create_access_token(user_id: int, role: str) -> str:
    """
    Criar JWT.

    Estrutura do JWT:
    ┌─────────────────────────────────────────┐
    │ HEADER: { alg: HS256, typ: JWT }        │
    ├─────────────────────────────────────────┤
    │ PAYLOAD: { sub: user_id, role, exp }    │
    ├─────────────────────────────────────────┤
    │ SIGNATURE: HMAC(header+payload+SECRET)  │
    └─────────────────────────────────────────┘

    Args:
        user_id: ID do usuário (sub)
        role: Permissão do usuário (USER, ADMIN, etc)

    Returns:
        JWT token (string)

    Raises:
        ValueError: Se SECRET_KEY não estiver configurada

    Example:
        token = create_access_token(user_id=1, role="USER")
        # token = "eyJhbGciOiJIUzI1NiIs..."
    """

    if not SECRET_KEY:
        raise ValueError(
            "❌ ERRO: SECRET_KEY não configurada no .env\n"
            "Gere com: openssl rand -hex 32"
        )

    if len(SECRET_KEY) < 32:
        raise ValueError(
            "❌ ERRO: SECRET_KEY muito curta (mínimo 32 caracteres)\n"
            "Gere com: openssl rand -hex 32"
        )

    # 👈 Calcular expiração
    expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # 👈 Criar payload (dados do token)
    payload = {
        "sub": str(user_id),              # subject = ID do usuário
        "role": role,                     # Permissão
        "exp": expires_at,                # Expiração
        "iat": datetime.utcnow()          # Emitido em
    }

    # 👈 Assinar e retornar token
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return token


def verify_token(token: str) -> dict | None:
    """
    Verificar JWT.

    Passos:
    1. Decodificar e verificar assinatura
    2. Verificar se não expirou
    3. Retornar payload se válido

    Args:
        token: JWT token (string)

    Returns:
        { "user_id": int, "role": str, "payload": dict }
        ou None se inválido/expirado

    Example:
        decoded = verify_token("eyJhbGciOiJIUzI1NiIs...")
        if decoded:
            print(f"User {decoded['user_id']} with role {decoded['role']}")
        else:
            print("Token inválido ou expirado")
    """

    if not SECRET_KEY:
        raise ValueError("SECRET_KEY não configurada")

    try:
        # 👈 Decodificar e verificar assinatura
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # 👈 Extrair dados (automaticamente valida "exp")
        user_id: str = payload.get("sub")
        role: str = payload.get("role")

        if user_id is None:
            return None

        return {
            "user_id": int(user_id),
            "role": role,
            "payload": payload
        }

    except JWTError:
        # 👈 Token inválido, expirado ou alterado
        # JWTError captura: ExpiredSignatureError, InvalidTokenError, etc
        return None


def decode_token_debug(token: str) -> dict | None:
    """
    Decodificar JWT SEM verificar assinatura.

    ⚠️ APENAS para debug! Não use em produção!

    Útil para ver o conteúdo do token no jwt.io ou manualmente.

    Args:
        token: JWT token

    Returns:
        Payload decodificado (sem verificação de segurança)
    """
    try:
        return jwt.get_unverified_claims(token)
    except:
        return None
