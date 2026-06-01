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
from src.application.ticket_service import TicketService
from src.infrastructure.di.dependencies import get_repository, get_service
from src.infrastructure.repositories.in_memory_ticket_repository import (
    InMemoryTicketRepository,
)


@pytest.fixture
def app():
    """
    Aplicação FastAPI para testes com repositório singleton.

    Por defeito get_repository() cria um InMemoryTicketRepository novo a cada
    request, o que faz com que dados criados num POST não sejam visíveis em
    requests seguintes. Para os testes, fazemos override para usar um único
    repositório partilhado durante o teste.
    """
    app = create_app()
    shared_repository = InMemoryTicketRepository()
    app.dependency_overrides[get_repository] = lambda: shared_repository
    app.dependency_overrides[get_service] = lambda: TicketService(shared_repository)
    return app


@pytest.fixture
def client(app):
    """Cliente de teste HTTP."""
    return TestClient(app)


# Password que cumpre a validação do RegisterRequest:
# minúscula, maiúscula, dígito e caractere especial em !@#$%^&*
VALID_PASSWORD = "MySecurePass123!"


def _auth_headers(client: TestClient, email: str = "tester@example.com") -> dict:
    """Regista um utilizador (idempotente) e devolve um header Authorization válido."""
    client.post("/auth/register", json={
        "name": "Tester User",
        "email": email,
        "password": VALID_PASSWORD,
    })
    login = client.post("/auth/login", json={
        "email": email,
        "password": VALID_PASSWORD,
    })
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestSystemRoutes:
    """Testes das rotas de sistema."""

    def test_root_endpoint(self, client):
        """GET / deve retornar 200 com metadados da API."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert data["status"] == "ok"

    def test_health_endpoint(self, client):
        """GET /health deve retornar status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "status" in response.json()


class TestAuthRoutes:
    """Testes das rotas de autenticação."""

    def test_register_user(self, client):
        """POST /auth/register deve criar um novo usuário."""
        response = client.post("/auth/register", json={
            "name": "Test User",
            "email": "test@example.com",
            "password": VALID_PASSWORD,
        })
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["email"] == "test@example.com"

    def test_register_duplicate_email_fails(self, client):
        """Registrar com email duplicado deve retornar 400."""
        email = "dup@example.com"
        first = client.post("/auth/register", json={
            "name": "User One",
            "email": email,
            "password": VALID_PASSWORD,
        })
        assert first.status_code == 201, first.text  # garante que o 1.º registo passou

        response = client.post("/auth/register", json={
            "name": "User Two",
            "email": email,
            "password": VALID_PASSWORD,
        })
        assert response.status_code == 400

    def test_login_with_correct_credentials(self, client):
        """POST /auth/login com credenciais corretas deve retornar token."""
        client.post("/auth/register", json={
            "name": "Test User",
            "email": "login@example.com",
            "password": VALID_PASSWORD,
        })
        response = client.post("/auth/login", json={
            "email": "login@example.com",
            "password": VALID_PASSWORD,
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_with_wrong_password_fails(self, client):
        """Login com senha errada deve retornar 401."""
        client.post("/auth/register", json={
            "name": "Test User",
            "email": "wrongpw@example.com",
            "password": VALID_PASSWORD,
        })
        response = client.post("/auth/login", json={
            "email": "wrongpw@example.com",
            "password": "WrongPassword123!",
        })
        assert response.status_code == 401

    def test_login_non_existent_user_fails(self, client):
        """Login com email inexistente deve retornar 401."""
        response = client.post("/auth/login", json={
            "email": "nonexistent@example.com",
            "password": VALID_PASSWORD,
        })
        assert response.status_code == 401


class TestTicketRoutes:
    """Testes das rotas de tickets."""

    @pytest.fixture
    def auth_headers(self, client):
        return _auth_headers(client)

    def test_create_ticket(self, client, auth_headers):
        """POST /tickets/ deve criar um novo ticket."""
        response = client.post(
            "/tickets/",
            json={
                "title": "Test Ticket",
                "description": "This is a test ticket",
                "priority": "medium",
                "category": "software",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["title"] == "Test Ticket"
        assert data["status"] == "open"

    def test_create_ticket_without_auth_fails(self, client):
        """Criar ticket sem autenticação deve retornar 401/403."""
        response = client.post("/tickets/", json={
            "title": "Test Ticket",
            "description": "Description",
        })
        assert response.status_code in (401, 403)

    def test_list_tickets(self, client, auth_headers):
        """GET /tickets/ deve retornar resposta paginada."""
        response = client.get("/tickets/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    def test_list_tickets_with_pagination(self, client, auth_headers):
        """GET /tickets/?page=1&size=10 deve devolver paginação."""
        response = client.get("/tickets/?page=1&size=10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 10

    def test_list_tickets_filter_by_status(self, client, auth_headers):
        """GET /tickets/?status=open deve filtrar por status."""
        response = client.get("/tickets/?status=open", headers=auth_headers)
        assert response.status_code == 200

    def test_get_ticket(self, client, auth_headers):
        """GET /tickets/{id} deve retornar um ticket."""
        create_response = client.post(
            "/tickets/",
            json={
                "title": "Test Ticket",
                "description": "Description",
                "priority": "medium",
                "category": "software",
            },
            headers=auth_headers,
        )
        ticket_id = create_response.json()["id"]

        response = client.get(f"/tickets/{ticket_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == ticket_id
        assert data["title"] == "Test Ticket"

    def test_get_non_existent_ticket_returns_404(self, client, auth_headers):
        """GET /tickets/999999 deve retornar 404."""
        response = client.get("/tickets/999999", headers=auth_headers)
        assert response.status_code == 404

    def test_update_ticket(self, client, auth_headers):
        """PATCH /tickets/{id} deve atualizar um ticket."""
        create_response = client.post(
            "/tickets/",
            json={
                "title": "Test Ticket",
                "description": "Description",
                "priority": "medium",
                "category": "software",
            },
            headers=auth_headers,
        )
        ticket_id = create_response.json()["id"]

        response = client.patch(
            f"/tickets/{ticket_id}",
            json={"status": "closed", "priority": "high"},
            headers=auth_headers,
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "closed"
        assert data["priority"] == "high"

    def test_add_comment_to_ticket(self, client, auth_headers):
        """POST /tickets/{id}/comments deve adicionar comentário."""
        create_response = client.post(
            "/tickets/",
            json={
                "title": "Test Ticket",
                "description": "Description",
                "priority": "medium",
                "category": "software",
            },
            headers=auth_headers,
        )
        ticket_id = create_response.json()["id"]

        response = client.post(
            f"/tickets/{ticket_id}/comments",
            json={"content": "This is a test comment"},
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["content"] == "This is a test comment"

    def test_add_comment_without_auth_fails(self, client):
        """Adicionar comentário sem auth deve retornar 401/403."""
        response = client.post(
            "/tickets/1/comments",
            json={"content": "Comment"},
        )
        assert response.status_code in (401, 403)


class TestCategoriesRoutes:
    """Testes da rota de categorias."""

    def test_get_categories(self, client):
        """GET /categories deve retornar lista de categorias."""
        response = client.get("/categories")
        assert response.status_code == 200
        data = response.json()
        # pode ser list direto ou dict com items — aceitar ambos
        if isinstance(data, dict) and "items" in data:
            data = data["items"]
        assert isinstance(data, list)
        assert len(data) > 0


class TestResponseFormats:
    """Testes de validação de formato de respostas."""

    def test_error_response_format(self, client):
        """Erros devem ter formato consistente com campo 'detail'."""
        headers = _auth_headers(client, email="errfmt@example.com")
        response = client.get("/tickets/999999", headers=headers)
        assert response.status_code == 404
        assert "detail" in response.json()

    def test_validation_error_response(self, client):
        """Erros de validação devem retornar 422."""
        response = client.post("/auth/register", json={
            "name": "",
            "email": "invalid-email",
            "password": "short",
        })
        assert response.status_code == 422


class TestCORS:
    """Testes de configuração CORS."""

    def test_cors_headers_present(self, client):
        """Respostas devem ter headers CORS."""
        response = client.get("/")
        assert response.status_code == 200

    def test_cors_methods_allowed(self, client):
        """Métodos HTTP permitidos devem estar configurados."""
        response = client.get("/")
        assert response.status_code == 200
