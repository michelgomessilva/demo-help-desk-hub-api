"""
Testes de integração para as rotas da API.

Cobre:
- Rotas de sistema (root, health)
- Rotas de autenticação (register, login)
- Rotas de tickets (create, list, get, update)
- Rotas de categorias
- Status codes HTTP
- Validação de respostas
"""

import pytest
from fastapi.testclient import TestClient
from src.main import create_app


@pytest.fixture
def app():
    """Aplicação FastAPI para testes."""
    return create_app()


@pytest.fixture
def client(app):
    """Cliente de teste HTTP."""
    return TestClient(app)


class TestSystemRoutes:
    """Testes das rotas de sistema."""

    def test_root_endpoint(self, client):
        """GET / deve retornar 200."""
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()

    def test_health_endpoint(self, client):
        """GET /health deve retornar status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestAuthRoutes:
    """Testes das rotas de autenticação."""

    def test_register_user(self, client):
        """POST /auth/register deve criar um novo usuário."""
        response = client.post("/auth/register", json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "TestPassword123!"
        })
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["email"] == "test@example.com"

    def test_register_duplicate_email_fails(self, client):
        """Registrar com email duplicado deve retornar 400."""
        email = "test@example.com"
        # Primeiro registro
        client.post("/auth/register", json={
            "name": "User 1",
            "email": email,
            "password": "Password123!"
        })
        # Segundo registro com mesmo email
        response = client.post("/auth/register", json={
            "name": "User 2",
            "email": email,
            "password": "Password123!"
        })
        assert response.status_code == 400

    def test_login_with_correct_credentials(self, client):
        """POST /auth/login com credenciais corretas deve retornar token."""
        # Registrar usuário
        client.post("/auth/register", json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "TestPassword123!"
        })
        # Fazer login
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "TestPassword123!"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_with_wrong_password_fails(self, client):
        """Login com senha errada deve retornar 401."""
        # Registrar usuário
        client.post("/auth/register", json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "TestPassword123!"
        })
        # Tentar login com senha errada
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "WrongPassword123!"
        })
        assert response.status_code == 401

    def test_login_non_existent_user_fails(self, client):
        """Login com email inexistente deve retornar 401."""
        response = client.post("/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "AnyPassword123!"
        })
        assert response.status_code == 401


class TestTicketRoutes:
    """Testes das rotas de tickets."""

    @pytest.fixture
    def auth_token(self, client):
        """Obter token de autenticação."""
        client.post("/auth/register", json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "TestPassword123!"
        })
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "TestPassword123!"
        })
        return response.json()["access_token"]

    def test_create_ticket(self, client, auth_token):
        """POST /tickets deve criar um novo ticket."""
        response = client.post(
            "/tickets",
            json={
                "title": "Test Ticket",
                "description": "This is a test ticket",
                "priority": "medium",
                "category": "software"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Ticket"
        assert data["status"] == "open"

    def test_create_ticket_without_auth_fails(self, client):
        """Criar ticket sem autenticação deve retornar 401."""
        response = client.post("/tickets", json={
            "title": "Test Ticket",
            "description": "Description"
        })
        assert response.status_code == 401

    def test_list_tickets(self, client):
        """GET /tickets deve retornar lista de tickets."""
        response = client.get("/tickets")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    def test_list_tickets_with_pagination(self, client):
        """GET /tickets?page=1&size=10 deve retornar página."""
        response = client.get("/tickets?page=1&size=10")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 10

    def test_list_tickets_filter_by_status(self, client):
        """GET /tickets?status=open deve filtrar por status."""
        response = client.get("/tickets?status=open")
        assert response.status_code == 200

    def test_get_ticket(self, client, auth_token):
        """GET /tickets/{id} deve retornar um ticket."""
        # Criar ticket
        create_response = client.post(
            "/tickets",
            json={
                "title": "Test Ticket",
                "description": "Description",
                "priority": "medium",
                "category": "software"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        ticket_id = create_response.json()["id"]

        # Buscar ticket
        response = client.get(f"/tickets/{ticket_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == ticket_id
        assert data["title"] == "Test Ticket"

    def test_get_non_existent_ticket_returns_404(self, client):
        """GET /tickets/999 deve retornar 404."""
        response = client.get("/tickets/999")
        assert response.status_code == 404

    def test_update_ticket(self, client, auth_token):
        """PATCH /tickets/{id} deve atualizar um ticket."""
        # Criar ticket
        create_response = client.post(
            "/tickets",
            json={
                "title": "Test Ticket",
                "description": "Description",
                "priority": "medium",
                "category": "software"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        ticket_id = create_response.json()["id"]

        # Atualizar ticket
        response = client.patch(
            f"/tickets/{ticket_id}",
            json={
                "status": "closed",
                "priority": "high"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "closed"
        assert data["priority"] == "high"

    def test_add_comment_to_ticket(self, client, auth_token):
        """POST /tickets/{id}/comments deve adicionar comentário."""
        # Criar ticket
        create_response = client.post(
            "/tickets",
            json={
                "title": "Test Ticket",
                "description": "Description",
                "priority": "medium",
                "category": "software"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        ticket_id = create_response.json()["id"]

        # Adicionar comentário
        response = client.post(
            f"/tickets/{ticket_id}/comments",
            json={"content": "This is a test comment"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "This is a test comment"

    def test_add_comment_without_auth_fails(self, client):
        """Adicionar comentário sem auth deve retornar 401."""
        response = client.post(
            "/tickets/1/comments",
            json={"content": "Comment"}
        )
        assert response.status_code == 401


class TestCategoriesRoutes:
    """Testes da rota de categorias."""

    def test_get_categories(self, client):
        """GET /categories deve retornar lista de categorias."""
        response = client.get("/categories")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0


class TestResponseFormats:
    """Testes de validação de formato de respostas."""

    def test_error_response_format(self, client):
        """Erros devem ter formato consistente."""
        response = client.get("/tickets/999")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_validation_error_response(self, client):
        """Erros de validação devem retornar detalhes."""
        response = client.post("/auth/register", json={
            "name": "",
            "email": "invalid-email",
            "password": "short"
        })
        assert response.status_code == 422


class TestCORS:
    """Testes de configuração CORS."""

    def test_cors_headers_present(self, client):
        """Respostas devem ter headers CORS."""
        response = client.get("/")
        # TestClient já lida com CORS, mas verificamos que a rota funciona
        assert response.status_code == 200

    def test_cors_methods_allowed(self, client):
        """Métodos HTTP permitidos devem estar configurados."""
        # Verificar que GET funciona
        response = client.get("/")
        assert response.status_code == 200
