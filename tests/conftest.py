"""
Configuração global de fixtures e setup para testes pytest.

Este arquivo é automaticamente descoberto pelo pytest e fornece:
- Fixtures para database sessions
- Fixtures para repositórios em memória
- Fixtures para aplicação FastAPI
- Fixtures para clientes HTTP de teste
"""

import pytest
from unittest.mock import Mock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from src.main import create_app
from src.infrastructure.database import Base
from src.infrastructure.repositories.in_memory_ticket_repository import InMemoryTicketRepository
from src.application.auth_service import AuthService
from src.application.ticket_service import TicketService
from src.domain.tickets.enums import TicketStatus, TicketPriority, TicketCategory
from src.domain.tickets.models import Ticket, Comment
from src.infrastructure.models.user_orm import UserORM


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture
def test_database_url():
    """URL de banco de dados de teste (SQLite em memória)."""
    return "sqlite:///:memory:"


@pytest.fixture
def test_engine(test_database_url):
    """Cria motor de banco de dados de teste."""
    engine = create_engine(test_database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def test_db_session(test_engine):
    """Cria uma sessão de banco de dados para testes."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


# ============================================================================
# REPOSITORY FIXTURES
# ============================================================================

@pytest.fixture
def in_memory_repository():
    """Repositório em memória limpo para cada teste."""
    return InMemoryTicketRepository()


# ============================================================================
# SERVICE FIXTURES
# ============================================================================

@pytest.fixture
def auth_service(test_db_session):
    """Serviço de autenticação com sessão de teste."""
    return AuthService(test_db_session)


@pytest.fixture
def ticket_service(in_memory_repository):
    """Serviço de tickets com repositório em memória."""
    return TicketService(in_memory_repository)


# ============================================================================
# FASTAPI APP FIXTURES
# ============================================================================

@pytest.fixture
def app():
    """Cria a aplicação FastAPI para testes."""
    return create_app()


@pytest.fixture
def client(app):
    """Cliente de teste para fazer requisições HTTP."""
    return TestClient(app)


# ============================================================================
# DATA FIXTURES - USUARIOS
# ============================================================================

@pytest.fixture
def test_user_data():
    """Dados de usuário para testes."""
    return {
        "name": "Test User",
        "email": "testuser@example.com",
        "password": "SecurePassword123!",
    }


@pytest.fixture
def test_admin_data():
    """Dados de usuário admin para testes."""
    return {
        "name": "Admin User",
        "email": "admin@example.com",
        "password": "AdminPassword123!",
    }


@pytest.fixture
def registered_user(test_db_session, test_user_data, auth_service):
    """Usuário registado no banco de dados."""
    user = auth_service.register(
        name=test_user_data["name"],
        email=test_user_data["email"],
        password=test_user_data["password"]
    )
    return user


# ============================================================================
# DATA FIXTURES - TICKETS
# ============================================================================

@pytest.fixture
def ticket_data():
    """Dados básicos de um ticket."""
    return {
        "title": "Test Ticket",
        "description": "This is a test ticket description",
        "priority": TicketPriority.MEDIUM,
        "category": TicketCategory.SOFTWARE,
    }


@pytest.fixture
def high_priority_ticket_data():
    """Dados de um ticket de alta prioridade."""
    return {
        "title": "Urgent Issue",
        "description": "This is an urgent issue that needs immediate attention",
        "priority": TicketPriority.HIGH,
        "category": TicketCategory.HARDWARE,
    }


@pytest.fixture
def created_ticket(ticket_service, ticket_data):
    """Ticket criado no repositório."""
    return ticket_service.create_ticket(
        title=ticket_data["title"],
        description=ticket_data["description"],
        priority=ticket_data["priority"],
        category=ticket_data["category"],
    )


@pytest.fixture
def comment_data():
    """Dados de um comentário."""
    return {"content": "This is a test comment"}


# ============================================================================
# MOCK FIXTURES
# ============================================================================

@pytest.fixture
def mock_repository():
    """Repositório mock para testes de service."""
    return MagicMock()


@pytest.fixture
def mock_db_session():
    """Sessão de banco de dados mock."""
    return MagicMock(spec=Session)


# ============================================================================
# HELPER FIXTURES
# ============================================================================

@pytest.fixture
def create_multiple_tickets(ticket_service):
    """Factory fixture para criar múltiplos tickets."""
    def _create(count: int = 5) -> list[Ticket]:
        tickets = []
        for i in range(count):
            ticket = ticket_service.create_ticket(
                title=f"Ticket {i+1}",
                description=f"Description {i+1}",
                priority=TicketPriority.MEDIUM if i % 2 == 0 else TicketPriority.HIGH,
                category=TicketCategory.SOFTWARE,
            )
            tickets.append(ticket)
        return tickets
    return _create
