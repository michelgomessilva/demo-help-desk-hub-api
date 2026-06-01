"""
Testes unitários para AuthService.

Cobre:
- Hash de senhas
- Verificação de senhas
- Registro de usuários
- Autenticação de usuários
- Validação de emails únicos
- Tratamento de erros
"""

import pytest
from fastapi import HTTPException, status
from src.application.auth_service import AuthService
from src.infrastructure.models.user_orm import UserORM


class TestPasswordHashing:
    """Testes de hash seguro de senhas."""

    def test_hash_password_returns_string(self, auth_service):
        """Hash deve retornar uma string."""
        password = "TestPassword123!"
        hashed = auth_service.hash_password(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_different_each_time(self, auth_service):
        """Cada hash deve ser diferente (sal aleatório)."""
        password = "TestPassword123!"
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)
        # Os hashes devem ser diferentes por causa do sal aleatório
        assert hash1 != hash2

    def test_hash_password_long_enough(self, auth_service):
        """Hash bcrypt deve ter um comprimento mínimo."""
        password = "TestPassword123!"
        hashed = auth_service.hash_password(password)
        # Hash bcrypt com rounds=12 tem típicamente ~60 caracteres
        assert len(hashed) >= 50

    def test_hash_short_password(self, auth_service):
        """Hash deve funcionar também com senhas curtas."""
        password = "a"
        hashed = auth_service.hash_password(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_with_special_chars(self, auth_service):
        """Hash deve lidar com caracteres especiais."""
        password = "P@ssw0rd!#$%^&*()"
        hashed = auth_service.hash_password(password)
        assert isinstance(hashed, str)


class TestPasswordVerification:
    """Testes de verificação de senhas."""

    def test_verify_correct_password(self, auth_service):
        """Deve retornar True para senha correta."""
        password = "TestPassword123!"
        hashed = auth_service.hash_password(password)
        assert auth_service.verify_password(password, hashed) is True

    def test_verify_incorrect_password(self, auth_service):
        """Deve retornar False para senha incorreta."""
        password = "TestPassword123!"
        hashed = auth_service.hash_password(password)
        assert auth_service.verify_password("WrongPassword", hashed) is False

    def test_verify_similar_password(self, auth_service):
        """Deve retornar False para senhas similares mas diferentes."""
        password = "TestPassword123!"
        hashed = auth_service.hash_password(password)
        assert auth_service.verify_password("TestPassword124!", hashed) is False

    def test_verify_case_sensitive(self, auth_service):
        """Verificação deve ser sensível a maiúsculas/minúsculas."""
        password = "TestPassword123!"
        hashed = auth_service.hash_password(password)
        assert auth_service.verify_password("testpassword123!", hashed) is False

    def test_verify_with_spaces(self, auth_service):
        """Espaços na senha devem ser significativos."""
        password = "Test Password 123"
        hashed = auth_service.hash_password(password)
        assert auth_service.verify_password("TestPassword123", hashed) is False
        assert auth_service.verify_password(password, hashed) is True

    def test_verify_invalid_hash_returns_false(self, auth_service):
        """Hash inválido deve retornar False em vez de lançar erro."""
        result = auth_service.verify_password("AnyPassword", "invalid_hash")
        assert result is False


class TestUserRegistration:
    """Testes de registro de novos usuários."""

    def test_register_user_successfully(self, auth_service, test_user_data):
        """Deve criar um novo usuário com sucesso."""
        user = auth_service.register(
            name=test_user_data["name"],
            email=test_user_data["email"],
            password=test_user_data["password"]
        )
        assert user.id is not None
        assert user.name == test_user_data["name"]
        assert user.email == test_user_data["email"]
        assert user.role == "USER"

    def test_register_user_password_hashed(self, auth_service, test_user_data):
        """Senha não deve ser armazenada em texto plano."""
        user = auth_service.register(
            name=test_user_data["name"],
            email=test_user_data["email"],
            password=test_user_data["password"]
        )
        # Verificar que a senha não é o texto plano armazenado
        assert user.password_hash != test_user_data["password"]
        # Mas o hash deve ser válido
        assert auth_service.verify_password(test_user_data["password"], user.password_hash)

    def test_register_duplicate_email_raises_error(self, auth_service, test_user_data):
        """Não deve permitir registrar dois usuários com o mesmo email."""
        # Registrar primeiro usuário
        auth_service.register(
            name=test_user_data["name"],
            email=test_user_data["email"],
            password=test_user_data["password"]
        )
        # Tentar registrar com o mesmo email deve falhar
        with pytest.raises(HTTPException) as exc_info:
            auth_service.register(
                name="Another Name",
                email=test_user_data["email"],
                password="AnotherPassword123!"
            )
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_different_emails_succeeds(self, auth_service):
        """Deve permitir registrar múltiplos usuários com emails diferentes."""
        user1 = auth_service.register(
            name="User One",
            email="user1@example.com",
            password="Password123!"
        )
        user2 = auth_service.register(
            name="User Two",
            email="user2@example.com",
            password="Password123!"
        )
        assert user1.id != user2.id
        assert user1.email != user2.email

    def test_register_preserves_user_data(self, auth_service):
        """Dados do usuário devem ser preservados."""
        user = auth_service.register(
            name="João Silva",
            email="joao@example.com",
            password="SenhaForte123!"
        )
        # Recuperar usuário do banco para verificar
        retrieved = auth_service.db.query(UserORM).filter(
            UserORM.email == "joao@example.com"
        ).first()
        assert retrieved.name == "João Silva"
        assert retrieved.email == "joao@example.com"


class TestUserAuthentication:
    """Testes de autenticação de usuários."""

    def test_authenticate_with_correct_credentials(self, auth_service, registered_user, test_user_data):
        """Deve autenticar com email e senha corretos."""
        user = auth_service.authenticate(
            email=test_user_data["email"],
            password=test_user_data["password"]
        )
        assert user is not None
        assert user.email == test_user_data["email"]
        assert user.id == registered_user.id

    def test_authenticate_with_wrong_password(self, auth_service, registered_user, test_user_data):
        """Deve retornar None com senha errada."""
        user = auth_service.authenticate(
            email=test_user_data["email"],
            password="WrongPassword123!"
        )
        assert user is None

    def test_authenticate_non_existent_email(self, auth_service):
        """Deve retornar None se email não existe."""
        user = auth_service.authenticate(
            email="nonexistent@example.com",
            password="AnyPassword123!"
        )
        assert user is None

    def test_authenticate_empty_email(self, auth_service, test_user_data):
        """Autenticação com email vazio deve falhar."""
        auth_service.register(
            name=test_user_data["name"],
            email=test_user_data["email"],
            password=test_user_data["password"]
        )
        user = auth_service.authenticate(
            email="",
            password=test_user_data["password"]
        )
        assert user is None

    def test_authenticate_empty_password(self, auth_service, registered_user, test_user_data):
        """Autenticação com senha vazia deve falhar."""
        user = auth_service.authenticate(
            email=test_user_data["email"],
            password=""
        )
        assert user is None

    def test_authenticate_returns_correct_user_fields(self, auth_service, registered_user, test_user_data):
        """Usuário autenticado deve ter todos os campos corretos."""
        user = auth_service.authenticate(
            email=test_user_data["email"],
            password=test_user_data["password"]
        )
        assert user.name == test_user_data["name"]
        assert user.email == test_user_data["email"]
        assert user.role == "USER"
        assert user.password_hash is not None


class TestAuthServiceEdgeCases:
    """Testes de casos extremos e validação."""

    def test_hash_very_long_password(self, auth_service):
        """Deve suportar senhas muito longas."""
        long_password = "a" * 1000
        hashed = auth_service.hash_password(long_password)
        assert auth_service.verify_password(long_password, hashed) is True

    def test_hash_unicode_characters(self, auth_service):
        """Deve suportar caracteres Unicode."""
        password = "SenhaÇom@Ç€ñtûs!😀"
        hashed = auth_service.hash_password(password)
        assert auth_service.verify_password(password, hashed) is True

    def test_register_user_with_unicode_name(self, auth_service):
        """Deve registrar usuário com nome em Unicode."""
        user = auth_service.register(
            name="José Pereira",
            email="jose@example.com",
            password="Password123!"
        )
        assert user.name == "José Pereira"

    def test_authenticate_multiple_users_independently(self, auth_service):
        """Autenticação de um usuário não deve afetar outro."""
        # Registrar dois usuários
        auth_service.register(
            name="User One",
            email="user1@example.com",
            password="Password1!"
        )
        auth_service.register(
            name="User Two",
            email="user2@example.com",
            password="Password2!"
        )
        # Verificar que cada um autentica independentemente
        user1 = auth_service.authenticate("user1@example.com", "Password1!")
        user2 = auth_service.authenticate("user2@example.com", "Password2!")
        assert user1 is not None
        assert user2 is not None
        assert user1.id != user2.id
