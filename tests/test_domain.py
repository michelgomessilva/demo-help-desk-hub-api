"""
Testes de domínio para modelos, enums e exceções.

Cobre:
- Criação de modelos de domínio
- Validação de enums
- Exceções de domínio
- Comportamentos esperados dos modelos
"""

import pytest
from datetime import datetime
from src.domain.tickets.models import Ticket, Comment
from src.domain.tickets.enums import TicketStatus, TicketPriority, TicketCategory
from src.domain.tickets.exceptions import TicketNotFoundError


class TestTicketModel:
    """Testes do modelo Ticket."""

    def test_create_ticket_with_minimal_args(self):
        """Deve criar um ticket com apenas id, title e description."""
        ticket = Ticket(
            id=1,
            title="Test Title",
            description="Test Description"
        )
        assert ticket.id == 1
        assert ticket.title == "Test Title"
        assert ticket.description == "Test Description"

    def test_ticket_default_status(self):
        """Status padrão deve ser OPEN."""
        ticket = Ticket(id=1, title="Title", description="Desc")
        assert ticket.status == TicketStatus.OPEN

    def test_ticket_default_priority(self):
        """Prioridade padrão deve ser MEDIUM."""
        ticket = Ticket(id=1, title="Title", description="Desc")
        assert ticket.priority == TicketPriority.MEDIUM

    def test_ticket_default_category(self):
        """Categoria padrão deve ser SOFTWARE."""
        ticket = Ticket(id=1, title="Title", description="Desc")
        assert ticket.category == TicketCategory.SOFTWARE

    def test_ticket_default_created_at(self):
        """created_at deve ser preenchido com data atual."""
        before = datetime.now()
        ticket = Ticket(id=1, title="Title", description="Desc")
        after = datetime.now()
        assert before <= ticket.created_at <= after

    def test_ticket_default_comments_empty(self):
        """Comentários padrão devem ser lista vazia."""
        ticket = Ticket(id=1, title="Title", description="Desc")
        assert ticket.comments == []
        assert isinstance(ticket.comments, list)

    def test_ticket_custom_created_at(self):
        """Deve aceitar created_at customizado."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        ticket = Ticket(
            id=1,
            title="Title",
            description="Desc",
            created_at=custom_time
        )
        assert ticket.created_at == custom_time

    def test_ticket_with_all_fields(self):
        """Deve aceitar todos os campos customizados."""
        custom_time = datetime(2024, 1, 1)
        ticket = Ticket(
            id=42,
            title="Important Bug",
            description="Critical issue",
            status=TicketStatus.IN_PROGRESS,
            priority=TicketPriority.URGENT,
            category=TicketCategory.HARDWARE,
            created_at=custom_time,
            comments=[]
        )
        assert ticket.id == 42
        assert ticket.title == "Important Bug"
        assert ticket.status == TicketStatus.IN_PROGRESS
        assert ticket.priority == TicketPriority.URGENT
        assert ticket.category == TicketCategory.HARDWARE

    def test_ticket_is_dataclass(self):
        """Ticket deve ser uma dataclass."""
        ticket = Ticket(id=1, title="Title", description="Desc")
        # Verificar que pode ser convertido para dict
        ticket_dict = ticket.__dict__
        assert isinstance(ticket_dict, dict)

    def test_ticket_can_be_modified(self):
        """Campos de ticket devem ser modificáveis."""
        ticket = Ticket(id=1, title="Title", description="Desc")
        ticket.status = TicketStatus.CLOSED
        ticket.priority = TicketPriority.HIGH
        assert ticket.status == TicketStatus.CLOSED
        assert ticket.priority == TicketPriority.HIGH


class TestCommentModel:
    """Testes do modelo Comment."""

    def test_create_comment_with_minimal_args(self):
        """Deve criar comentário com id, ticket_id e content."""
        comment = Comment(
            id=1,
            ticket_id=10,
            content="Test comment"
        )
        assert comment.id == 1
        assert comment.ticket_id == 10
        assert comment.content == "Test comment"

    def test_comment_default_created_at(self):
        """created_at deve ser preenchido com data atual."""
        before = datetime.now()
        comment = Comment(id=1, ticket_id=10, content="Content")
        after = datetime.now()
        assert before <= comment.created_at <= after

    def test_comment_custom_created_at(self):
        """Deve aceitar created_at customizado."""
        custom_time = datetime(2024, 1, 1, 15, 30, 0)
        comment = Comment(
            id=1,
            ticket_id=10,
            content="Content",
            created_at=custom_time
        )
        assert comment.created_at == custom_time

    def test_comment_can_have_long_content(self):
        """Comment deve aceitar conteúdo longo."""
        long_content = "a" * 10000
        comment = Comment(
            id=1,
            ticket_id=10,
            content=long_content
        )
        assert len(comment.content) == 10000

    def test_comment_is_dataclass(self):
        """Comment deve ser uma dataclass."""
        comment = Comment(id=1, ticket_id=10, content="Content")
        comment_dict = comment.__dict__
        assert isinstance(comment_dict, dict)


class TestTicketStatusEnum:
    """Testes do enum TicketStatus."""

    def test_all_status_values_exist(self):
        """Todos os status esperados devem existir."""
        assert hasattr(TicketStatus, "OPEN")
        assert hasattr(TicketStatus, "IN_PROGRESS")
        assert hasattr(TicketStatus, "CLOSED")

    def test_status_has_string_value(self):
        """Status deve ter valor string."""
        assert isinstance(TicketStatus.OPEN.value, str)
        assert TicketStatus.OPEN.value == "open"

    def test_status_comparison(self):
        """Status devem ser comparáveis."""
        assert TicketStatus.OPEN == TicketStatus.OPEN
        assert TicketStatus.OPEN != TicketStatus.CLOSED

    def test_can_iterate_status(self):
        """Deve ser possível iterar sobre status."""
        statuses = list(TicketStatus)
        assert len(statuses) > 0


class TestTicketPriorityEnum:
    """Testes do enum TicketPriority."""

    def test_all_priority_values_exist(self):
        """Todas as prioridades esperadas devem existir."""
        assert hasattr(TicketPriority, "LOW")
        assert hasattr(TicketPriority, "MEDIUM")
        assert hasattr(TicketPriority, "HIGH")
        assert hasattr(TicketPriority, "URGENT")

    def test_priority_has_string_value(self):
        """Prioridade deve ter valor string."""
        assert isinstance(TicketPriority.HIGH.value, str)

    def test_priority_comparison(self):
        """Prioridades devem ser comparáveis."""
        assert TicketPriority.HIGH == TicketPriority.HIGH
        assert TicketPriority.HIGH != TicketPriority.LOW

    def test_can_iterate_priorities(self):
        """Deve ser possível iterar sobre prioridades."""
        priorities = list(TicketPriority)
        assert len(priorities) == 4


class TestTicketCategoryEnum:
    """Testes do enum TicketCategory."""

    def test_all_category_values_exist(self):
        """Todas as categorias esperadas devem existir."""
        assert hasattr(TicketCategory, "SOFTWARE")
        assert hasattr(TicketCategory, "HARDWARE")
        assert hasattr(TicketCategory, "NETWORK")
        assert hasattr(TicketCategory, "ACCESS")

    def test_category_has_string_value(self):
        """Categoria deve ter valor string."""
        assert isinstance(TicketCategory.SOFTWARE.value, str)

    def test_category_comparison(self):
        """Categorias devem ser comparáveis."""
        assert TicketCategory.SOFTWARE == TicketCategory.SOFTWARE
        assert TicketCategory.SOFTWARE != TicketCategory.HARDWARE

    def test_can_iterate_categories(self):
        """Deve ser possível iterar sobre categorias."""
        categories = list(TicketCategory)
        assert len(categories) > 0


class TestTicketNotFoundError:
    """Testes da exceção TicketNotFoundError."""

    def test_raise_ticket_not_found_error(self):
        """Deve ser possível lançar TicketNotFoundError."""
        with pytest.raises(TicketNotFoundError):
            raise TicketNotFoundError(999)

    def test_ticket_not_found_error_message(self):
        """TicketNotFoundError deve ter mensagem clara."""
        try:
            raise TicketNotFoundError(123)
        except TicketNotFoundError as e:
            assert "123" in str(e)

    def test_ticket_not_found_error_is_exception(self):
        """TicketNotFoundError deve ser uma Exception."""
        assert issubclass(TicketNotFoundError, Exception)

    def test_catch_ticket_not_found_error(self):
        """Deve ser possível capturar TicketNotFoundError."""
        try:
            raise TicketNotFoundError(999)
        except TicketNotFoundError:
            pass  # Esperado
        except Exception:
            pytest.fail("TicketNotFoundError não foi capturado")


class TestModelRelationships:
    """Testes de relacionamentos entre modelos."""

    def test_ticket_can_have_comments(self):
        """Ticket pode ter uma lista de comentários."""
        ticket = Ticket(id=1, title="Title", description="Desc")
        comment = Comment(id=1, ticket_id=1, content="Comment")
        ticket.comments.append(comment)

        assert len(ticket.comments) == 1
        assert ticket.comments[0].ticket_id == ticket.id

    def test_multiple_comments_on_ticket(self):
        """Ticket pode ter múltiplos comentários."""
        ticket = Ticket(id=1, title="Title", description="Desc")
        for i in range(5):
            comment = Comment(id=i+1, ticket_id=1, content=f"Comment {i+1}")
            ticket.comments.append(comment)

        assert len(ticket.comments) == 5

    def test_comment_ticket_id_consistency(self):
        """ticket_id do comment deve ser consistente."""
        ticket = Ticket(id=42, title="Title", description="Desc")
        comment = Comment(id=1, ticket_id=42, content="Comment")
        ticket.comments.append(comment)

        assert comment.ticket_id == ticket.id
