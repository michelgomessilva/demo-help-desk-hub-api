"""
Handler de JWT.

Responsável por:
- Gerar JWT (create_access_token)
- Verificar JWT (verify_token)
"""

import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
from src.infrastructure.logging_config import get_logger

# 👈 Obter logger estruturado
logger = get_logger(__name__)


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
    # 👈 Debug: iniciar criação de token
    logger.debug("creating_jwt_token", user_id=user_id, role=role)

    if not SECRET_KEY:
        logger.error("create_token_failed", reason="SECRET_KEY not configured")
        raise ValueError(
            "❌ ERRO: SECRET_KEY não configurada no .env\n"
            "Gere com: openssl rand -hex 32"
        )

    if len(SECRET_KEY) < 32:
        logger.error("create_token_failed", reason="SECRET_KEY too short", secret_key_length=len(SECRET_KEY))
        raise ValueError(
            "❌ ERRO: SECRET_KEY muito curta (mínimo 32 caracteres)\n"
            "Gere com: openssl rand -hex 32"
        )

    # 👈 Debug: calcular expiração
    expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    logger.debug("token_expiration_calculated", user_id=user_id, expires_in_minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # 👈 Debug: criar payload
    payload = {
        "sub": str(user_id),              # subject = ID do usuário
        "role": role,                     # Permissão
        "exp": expires_at,                # Expiração
        "iat": datetime.utcnow()          # Emitido em
    }

    try:
        # 👈 Debug: assinar token
        logger.debug("encoding_jwt_token", user_id=user_id, algorithm=ALGORITHM)
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        # 👈 Info: token criado com sucesso
        logger.info("jwt_token_created_successfully", user_id=user_id, role=role, token_length=len(token))
        return token
    except Exception as e:
        logger.error("token_creation_error", user_id=user_id, error=str(e), error_type=type(e).__name__)
        raise


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
    # 👈 Debug: iniciar verificação de token
    logger.debug("verifying_jwt_token", token_length=len(token))

    if not SECRET_KEY:
        logger.error("verify_token_failed", reason="SECRET_KEY not configured")
        raise ValueError("SECRET_KEY não configurada")

    try:
        # 👈 Debug: decodificar e verificar assinatura
        logger.debug("decoding_jwt_token")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # 👈 Debug: extrair dados
        user_id: str = payload.get("sub")
        role: str = payload.get("role")

        if user_id is None:
            logger.warning("token_verification_failed", reason="no_subject_claim")
            return None

        # 👈 Info: token verificado com sucesso
        logger.info("jwt_token_verified_successfully", user_id=int(user_id), role=role)
        return {
            "user_id": int(user_id),
            "role": role,
            "payload": payload
        }

    except JWTError as e:
        # 👈 Warning: token inválido, expirado ou alterado
        # JWTError captura: ExpiredSignatureError, InvalidTokenError, etc
        logger.warning("token_verification_failed", reason="jwt_error", error_type=type(e).__name__)
        return None
    except Exception as e:
        logger.error("token_verification_error", error=str(e), error_type=type(e).__name__)
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
    # 👈 Warning: decodificação sem verificação
    logger.warning("debug_token_decode_called", token_length=len(token), reason="unverified_decode")

    try:
        # 👈 Debug: decodificar sem verificar
        claims = jwt.get_unverified_claims(token)
        logger.debug("debug_token_decoded_successfully", user_id=claims.get("sub"))
        return claims
    except Exception as e:
        logger.error("debug_token_decode_error", error=str(e), error_type=type(e).__name__)
        return None
