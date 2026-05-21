"""
Authentication service with password hashing and user management.

Responsible for:
- Secure password hashing with bcrypt
- Password verification
- User registration and authentication
"""

import bcrypt
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from src.infrastructure.models.user_orm import UserORM
from src.infrastructure.logging_config import get_logger

# 👈 Obter logger estruturado
logger = get_logger(__name__)


class AuthService:
    """
    Serviço de autenticação e gerenciamento de senhas.

    Usa bcrypt para hash seguro de senhas.
    """

    def __init__(self, db: Session):
        self.db = db

    def hash_password(self, plain_password: str) -> str:
        """
        Gerar hash bcrypt da senha.

        Exemplo:
            plain: "admin123"
            hash:  "$2b$12$abc...xyz" (único para esta senha + salt)

        Args:
            plain_password: Senha em texto plano

        Returns:
            Hash bcrypt (string)
        """
        # 👈 Debug: iniciar hashing
        logger.debug("password_hashing_started", password_length=len(plain_password))

        try:
            # 👈 Codificar string para bytes (bcrypt precisa de bytes)
            password_bytes = plain_password.encode('utf-8')

            # 👈 gensalt() gera salt aleatório automaticamente
            # 12 = custo (quanto mais alto, mais seguro mas mais lento)
            salt = bcrypt.gensalt(rounds=12)

            # 👈 Hash: combina senha + salt, resultado determinístico
            hashed = bcrypt.hashpw(password_bytes, salt)

            # 👈 Converter bytes de volta para string
            logger.debug("password_hashing_completed", hash_length=len(hashed.decode('utf-8')))
            return hashed.decode('utf-8')
        except Exception as e:
            logger.error("password_hashing_failed", error=str(e), error_type=type(e).__name__)
            raise

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verificar se a senha está correta.

        bcrypt.checkpw() é seguro contra timing attacks!

        Exemplo:
            user digita: "admin123"
            checkpw compara com hash armazenado
            resultado: True ou False

        Args:
            plain_password: Senha que o usuário digitou
            hashed_password: Hash armazenado no banco

        Returns:
            True se correto, False caso contrário
        """
        # 👈 Debug: iniciar verificação
        logger.debug("password_verification_started")

        try:
            password_bytes = plain_password.encode('utf-8')
            hashed_bytes = hashed_password.encode('utf-8')
            result = bcrypt.checkpw(password_bytes, hashed_bytes)

            if result:
                logger.debug("password_verification_succeeded")
            else:
                logger.warning("password_verification_failed", reason="password_mismatch")

            return result
        except Exception as e:
            # 👈 Erro ao verificar = senha incorreta
            logger.warning("password_verification_error", error=str(e), error_type=type(e).__name__)
            return False

    def register(self, name: str, email: str, password: str) -> UserORM:
        """
        Registrar novo usuário.

        Passos:
        1. Verificar se email já existe
        2. Hash da senha com bcrypt
        3. Criar usuário no banco
        4. Retornar usuário criado

        Args:
            name: Nome do usuário
            email: Email do usuário (único)
            password: Senha em texto plano

        Returns:
            UserORM objeto criado

        Raises:
            HTTPException: Se email já existir
        """
        # 👈 Info: iniciar registro
        logger.info("user_registration_started", email=email, name=name)

        # 👈 Verificar se email já existe
        logger.debug("checking_email_existence", email=email)
        existing = self.db.query(UserORM).filter(
            UserORM.email == email
        ).first()

        if existing:
            logger.warning("user_registration_failed", email=email, reason="email_already_exists")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já cadastrado"
            )

        logger.debug("email_is_available", email=email)

        # 👈 Hash da senha
        logger.debug("hashing_password", email=email)
        hashed_password = self.hash_password(password)

        # 👈 Criar usuário
        logger.debug("creating_user_object", email=email, role="USER")
        user = UserORM(
            name=name,
            email=email,
            password_hash=hashed_password,  # Guardar HASH, não a senha!
            role="USER"
        )

        # 👈 Salvar no banco
        try:
            logger.debug("saving_user_to_database", email=email)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)

            logger.info("user_registration_completed", user_id=user.id, email=email, name=name)
            return user
        except Exception as e:
            self.db.rollback()
            logger.error(
                "user_registration_database_error",
                email=email,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    def authenticate(self, email: str, password: str) -> UserORM | None:
        """
        Autenticar usuário (login).

        Passos:
        1. Buscar usuário por email
        2. Verificar se senha está correta
        3. Retornar usuário se correto, None se incorreto

        Args:
            email: Email do usuário
            password: Senha em texto plano

        Returns:
            UserORM se autenticado, None caso contrário
        """
        # 👈 Info: iniciar autenticação
        logger.info("authentication_attempt_started", email=email)

        # 👈 Debug: buscar usuário
        logger.debug("looking_up_user_by_email", email=email)
        user = self.db.query(UserORM).filter(
            UserORM.email == email
        ).first()

        if not user:
            # 👈 Warning: usuário não encontrado
            logger.warning(
                "authentication_failed_user_not_found",
                email=email,
                reason="user_not_exists"
            )
            return None

        logger.debug("user_found_checking_password", user_id=user.id, email=email)

        # 👈 Verificar senha com bcrypt
        if not self.verify_password(password, user.password_hash):
            # 👈 Warning: senha incorreta
            logger.warning(
                "authentication_failed_invalid_password",
                user_id=user.id,
                email=email,
                reason="password_mismatch"
            )
            return None

        # 👈 Info: autenticação bem-sucedida
        logger.info("authentication_succeeded", user_id=user.id, email=email, user_name=user.name)
        return user
