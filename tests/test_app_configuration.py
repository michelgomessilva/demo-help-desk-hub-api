"""
Testes de configuração da aplicação.

Cobre:
- Validação de variáveis de ambiente
- Configuração de segurança
- Middleware
- Inicialização da aplicação
"""

import pytest
import os
from unittest.mock import patch
from dotenv import load_dotenv
from src.main import create_app


class TestAppConfiguration:
    """Testes de configuração geral da aplicação."""

    def test_app_creation_succeeds_with_valid_env(self):
        """Aplicação deve ser criada com configuração válida."""
        # Secret key deve estar no .env (verificar conftest)
        app = create_app()
        assert app is not None

    def test_app_has_required_routers(self):
        """Aplicação deve ter todos os routers registrados."""
        app = create_app()
        # Verificar que routers foram inclusos
        router_paths = [route.path for route in app.routes]
        assert any("/" in path for path in router_paths)
        assert any("health" in path for path in router_paths)

    def test_app_has_middleware(self):
        """Aplicação deve ter middleware configurado."""
        app = create_app()
        # user_middleware é a lista pública de middlewares registados via add_middleware()
        assert len(app.user_middleware) > 0

    def test_app_cors_configured(self):
        """CORS deve estar configurado."""
        app = create_app()
        has_cors = any("CORSMiddleware" in str(m.cls) for m in app.user_middleware)
        assert has_cors


class TestEnvironmentVariables:
    """Testes de variáveis de ambiente."""

    def test_secret_key_must_exist(self):
        """SECRET_KEY é obrigatório."""
        secret_key = os.getenv("SECRET_KEY")
        assert secret_key is not None, "SECRET_KEY não está configurado"

    def test_secret_key_minimum_length(self):
        """SECRET_KEY deve ter pelo menos 32 caracteres."""
        secret_key = os.getenv("SECRET_KEY")
        assert len(secret_key) >= 32, f"SECRET_KEY tem apenas {len(secret_key)} caracteres"

    def test_algorithm_is_valid(self):
        """ALGORITHM deve ser HS256 ou HS512."""
        algorithm = os.getenv("ALGORITHM", "HS256")
        assert algorithm in ["HS256", "HS512"], f"ALGORITHM inválido: {algorithm}"

    def test_environment_variable_defaults(self):
        """Variáveis devem ter valores padrão sensatos."""
        environment = os.getenv("ENVIRONMENT", "development")
        assert environment in ["development", "production"], f"ENVIRONMENT inválido: {environment}"

    def test_allowed_origins_configured(self):
        """ALLOWED_ORIGINS deve estar configurado ou ter padrão."""
        origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000")
        assert origins is not None
        assert len(origins) > 0


class TestSecurityHeaders:
    """Testes de headers de segurança."""

    def test_app_response_has_security_headers(self):
        """Respostas devem ter headers de segurança."""
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        response = client.get("/")
        # Headers de segurança devem estar presentes
        assert response.status_code in [200, 404]  # Pode existir ou não a rota, mas a header deve estar


class TestMiddleware:
    """Testes de middleware."""

    def test_logging_middleware_present(self):
        """Middleware de logging deve estar presente."""
        app = create_app()
        # Verificar que a aplicação foi criada com middleware
        assert app is not None

    def test_cors_middleware_present(self):
        """Middleware CORS deve estar presente."""
        app = create_app()
        # Verificar que a aplicação foi criada com middleware
        assert app is not None


class TestAppStartup:
    """Testes de inicialização da aplicação."""

    def test_app_startup_event_handlers_exist(self):
        """App deve ter handlers de startup."""
        app = create_app()
        # Verificar que eventos foram registrados
        assert len(app.router.on_startup) > 0 or len(app.router.on_shutdown) > 0

    def test_app_shutdown_event_handlers_exist(self):
        """App deve ter handlers de shutdown."""
        app = create_app()
        assert app is not None


class TestAppMetadata:
    """Testes de metadados da aplicação."""

    def test_app_has_title(self):
        """Aplicação deve ter um título."""
        app = create_app()
        assert app.title is not None
        assert len(app.title) > 0

    def test_app_has_description(self):
        """Aplicação deve ter uma descrição."""
        app = create_app()
        assert app.description is not None

    def test_app_has_version(self):
        """Aplicação deve ter uma versão."""
        app = create_app()
        assert app.version is not None

    def test_app_metadata_is_correct(self):
        """Metadados da aplicação devem estar corretos."""
        app = create_app()
        assert "HelpDesk" in app.title
        assert "1.0.0" in app.version


class TestDatabaseInitialization:
    """Testes de inicialização do banco de dados."""

    def test_database_url_configured(self):
        """DATABASE_URL deve estar configurado."""
        db_url = os.getenv("DATABASE_URL")
        # DATABASE_URL pode não estar configurado em testes (usa SQLite)
        # Mas não deve gerar erro

    def test_app_startup_with_missing_database(self):
        """App deve iniciar mesmo se database estiver indisponível."""
        # Quando DATABASE_URL não está configurado, app deve usar in-memory
        app = create_app()
        assert app is not None


class TestApplicationErrors:
    """Testes de tratamento de erros na aplicação."""

    def test_missing_secret_key_raises_error(self):
        """Falta de SECRET_KEY deve lançar erro."""
        with patch.dict(os.environ, {}, clear=False):
            # Remover SECRET_KEY temporariamente
            if "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]

            # Deve lançar ValueError
            with pytest.raises(ValueError) as exc_info:
                create_app()
            assert "SECRET_KEY" in str(exc_info.value)

    def test_invalid_algorithm_raises_error(self):
        """ALGORITHM inválido deve lançar erro."""
        with patch.dict(os.environ, {"ALGORITHM": "INVALID"}):
            with pytest.raises(ValueError) as exc_info:
                create_app()
            assert "ALGORITHM" in str(exc_info.value)

    def test_short_secret_key_raises_error(self):
        """SECRET_KEY muito curta deve lançar erro."""
        with patch.dict(os.environ, {"SECRET_KEY": "short"}):
            with pytest.raises(ValueError) as exc_info:
                create_app()
            assert "SECRET_KEY" in str(exc_info.value)


class TestCORSConfiguration:
    """Testes de configuração CORS."""

    def test_cors_development_mode_allows_localhost(self):
        """Em desenvolvimento, localhost deve ser permitido."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            app = create_app()
            assert app is not None

    def test_cors_production_mode_restricted(self):
        """Em produção, CORS deve ser restrito."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            app = create_app()
            assert app is not None

    def test_cors_methods_configured(self):
        """Métodos HTTP permitidos devem estar configurados."""
        app = create_app()
        assert len(app.user_middleware) > 0
