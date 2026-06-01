"""
Testes unitários para InMemoryTicketRepository.

Cobre:
- Criação e armazenamento de tickets
- Busca e recuperação de tickets
- Atualização de tickets
- Listagem com filtros e paginação
- Gerenciamento de comentários
- Casos extremos e validação
"""

import pytest
from src.infrastructure.repositories.in_memory_ticket_repository import InMemoryTicketRepository
from src.domain.tickets.models import Ticket, Comment
from src.domain.tickets.enums import TicketStatus, TicketPriority, TicketCategory
from datetime import datetime


class TestInMemoryRepositoryCreate:
    """Testes de criação de tickets no repositório em memória."""

    def test_create_ticket_assigns_unique_id(self, in_memory_repository):
        """Cada ticket criado deve ter um ID único."""
        ticket1 = Ticket(
            id=0,
            title="Ticket 1",
            description="Description 1"
        )
        ticket2 = Ticket(
            id=0,
            title="Ticket 2",
            description="Description 2"
        )

        created1 = in_memory_repository.create(ticket1)
        created2 = in_memory_repository.create(ticket2)

        assert created1.id != created2.id
        assert created1.id == 1
        assert created2.id == 2

    def test_create_ticket_returns_same_object(self, in_memory_repository):
        """create() deve retornar o objeto ticket com ID atribuído."""
        ticket = Ticket(
            id=0,
            title="Test",
            description="Test"
        )
        created = in_memory_repository.create(ticket)
        assert created.id > 0
        assert created.title == ticket.title

    def test_create_none_ticket_raises_error(self, in_memory_repository):
        """Criar None deve lançar ValueError."""
        with pytest.raises(ValueError):
            in_memory_repository.create(None)

    def test_create_multiple_tickets(self, in_memory_repository):
        """Deve criar múltiplos tickets sequencialmente."""
        for i in range(5):
            ticket = Ticket(
                id=0,
                title=f"Ticket {i}",
                description=f"Description {i}"
            )
            created = in_memory_repository.create(ticket)
            assert created.id == i + 1


class TestInMemoryRepositoryGetById:
    """Testes de busca por ID."""

    def test_get_existing_ticket(self, in_memory_repository):
        """Deve retornar um ticket existente."""
        ticket = Ticket(id=0, title="Test", description="Test")
        created = in_memory_repository.create(ticket)

        retrieved = in_memory_repository.get_by_id(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == created.title

    def test_get_non_existent_ticket_returns_none(self, in_memory_repository):
        """Buscar ID inexistente deve retornar None."""
        result = in_memory_repository.get_by_id(999)
        assert result is None

    def test_get_ticket_preserves_data(self, in_memory_repository):
        """Dados do ticket devem ser preservados."""
        ticket = Ticket(
            id=0,
            title="Test Title",
            description="Test Description",
            priority=TicketPriority.HIGH,
            category=TicketCategory.HARDWARE
        )
        created = in_memory_repository.create(ticket)
        retrieved = in_memory_repository.get_by_id(created.id)

        assert retrieved.title == "Test Title"
        assert retrieved.description == "Test Description"
        assert retrieved.priority == TicketPriority.HIGH
        assert retrieved.category == TicketCategory.HARDWARE


class TestInMemoryRepositoryGetAll:
    """Testes de listagem de todos os tickets."""

    def test_get_all_empty_repository(self, in_memory_repository):
        """Repositório vazio deve retornar ([], 0)."""
        tickets, total = in_memory_repository.get_all()
        assert tickets == []
        assert total == 0

    def test_get_all_returns_all_tickets(self, in_memory_repository):
        """Deve retornar todos os tickets criados."""
        for i in range(5):
            ticket = Ticket(id=0, title=f"Ticket {i}", description=f"Desc {i}")
            in_memory_repository.create(ticket)

        tickets, total = in_memory_repository.get_all()
        assert len(tickets) == 5
        assert total == 5

    def test_get_all_with_pagination_default(self, in_memory_repository):
        """Paginação padrão deve retornar até 10 items."""
        for i in range(15):
            ticket = Ticket(id=0, title=f"Ticket {i}", description=f"Desc {i}")
            in_memory_repository.create(ticket)

        tickets, total = in_memory_repository.get_all(page=1, size=10)
        assert len(tickets) == 10
        assert total == 15

    def test_get_all_pagination_page_2(self, in_memory_repository):
        """Segunda página deve retornar items restantes."""
        for i in range(15):
            ticket = Ticket(id=0, title=f"Ticket {i}", description=f"Desc {i}")
            in_memory_repository.create(ticket)

        page1, total1 = in_memory_repository.get_all(page=1, size=10)
        page2, total2 = in_memory_repository.get_all(page=2, size=10)

        assert len(page1) == 10
        assert len(page2) == 5
        assert total1 == 15
        assert total2 == 15

    def test_get_all_invalid_page_defaults_to_1(self, in_memory_repository):
        """Página < 1 deve ser ajustada para 1."""
        ticket = Ticket(id=0, title="Test", description="Test")
        in_memory_repository.create(ticket)

        tickets, _ = in_memory_repository.get_all(page=0, size=10)
        assert len(tickets) > 0

    def test_get_all_invalid_size_defaults_to_10(self, in_memory_repository):
        """Size < 1 deve ser ajustado para 10."""
        ticket = Ticket(id=0, title="Test", description="Test")
        in_memory_repository.create(ticket)

        tickets, _ = in_memory_repository.get_all(page=1, size=0)
        assert len(tickets) > 0

    def test_get_all_filter_by_status(self, in_memory_repository):
        """Deve filtrar por status."""
        t1 = Ticket(id=0, title="T1", description="D1", status=TicketStatus.OPEN)
        t2 = Ticket(id=0, title="T2", description="D2", status=TicketStatus.CLOSED)

        in_memory_repository.create(t1)
        in_memory_repository.create(t2)

        tickets, total = in_memory_repository.get_all(status=TicketStatus.OPEN)
        assert len(tickets) == 1
        assert total == 1
        assert tickets[0].status == TicketStatus.OPEN

    def test_get_all_filter_by_priority(self, in_memory_repository):
        """Deve filtrar por prioridade."""
        t1 = Ticket(id=0, title="T1", description="D1", priority=TicketPriority.HIGH)
        t2 = Ticket(id=0, title="T2", description="D2", priority=TicketPriority.LOW)

        in_memory_repository.create(t1)
        in_memory_repository.create(t2)

        tickets, total = in_memory_repository.get_all(priority=TicketPriority.HIGH)
        assert len(tickets) == 1
        assert tickets[0].priority == TicketPriority.HIGH

    def test_get_all_filter_by_category(self, in_memory_repository):
        """Deve filtrar por categoria."""
        t1 = Ticket(id=0, title="T1", description="D1", category=TicketCategory.HARDWARE)
        t2 = Ticket(id=0, title="T2", description="D2", category=TicketCategory.SOFTWARE)

        in_memory_repository.create(t1)
        in_memory_repository.create(t2)

        tickets, total = in_memory_repository.get_all(category=TicketCategory.HARDWARE)
        assert len(tickets) == 1
        assert tickets[0].category == TicketCategory.HARDWARE

    def test_get_all_multiple_filters(self, in_memory_repository):
        """Deve filtrar com múltiplos critérios."""
        t1 = Ticket(
            id=0, title="T1", description="D1",
            status=TicketStatus.OPEN,
            priority=TicketPriority.HIGH,
            category=TicketCategory.HARDWARE
        )
        t2 = Ticket(
            id=0, title="T2", description="D2",
            status=TicketStatus.CLOSED,
            priority=TicketPriority.HIGH,
            category=TicketCategory.SOFTWARE
        )

        in_memory_repository.create(t1)
        in_memory_repository.create(t2)

        tickets, _ = in_memory_repository.get_all(
            status=TicketStatus.OPEN,
            priority=TicketPriority.HIGH,
            category=TicketCategory.HARDWARE
        )
        assert len(tickets) == 1
        assert tickets[0].id == 1


class TestInMemoryRepositoryUpdate:
    """Testes de atualização de tickets."""

    def test_update_existing_ticket(self, in_memory_repository):
        """Deve atualizar um ticket existente."""
        ticket = Ticket(
            id=0, title="Original", description="Original",
            status=TicketStatus.OPEN
        )
        created = in_memory_repository.create(ticket)

        created.status = TicketStatus.CLOSED
        updated = in_memory_repository.update(created)

        assert updated.status == TicketStatus.CLOSED
        assert updated.title == "Original"

    def test_update_non_existent_ticket_raises_error(self, in_memory_repository):
        """Atualizar ticket inexistente deve falhar."""
        ticket = Ticket(id=999, title="Test", description="Test")
        with pytest.raises(ValueError):
            in_memory_repository.update(ticket)

    def test_update_preserves_other_fields(self, in_memory_repository):
        """Atualizar um campo não deve afetar outros."""
        ticket = Ticket(
            id=0, title="Title", description="Desc",
            priority=TicketPriority.LOW,
            category=TicketCategory.SOFTWARE
        )
        created = in_memory_repository.create(ticket)
        created.status = TicketStatus.IN_PROGRESS

        updated = in_memory_repository.update(created)
        assert updated.title == "Title"
        assert updated.description == "Desc"
        assert updated.priority == TicketPriority.LOW

    def test_update_none_ticket_raises_error(self, in_memory_repository):
        """Atualizar None deve falhar."""
        with pytest.raises(ValueError):
            in_memory_repository.update(None)

    def test_update_ticket_with_invalid_id_raises_error(self, in_memory_repository):
        """Ticket com ID <= 0 deve ser rejeitado."""
        ticket = Ticket(id=0, title="Test", description="Test")
        with pytest.raises(ValueError):
            in_memory_repository.update(ticket)


class TestInMemoryRepositoryComments:
    """Testes de gerenciamento de comentários."""

    def test_add_comment_successfully(self, in_memory_repository):
        """Deve adicionar um comentário a um ticket."""
        ticket = Ticket(id=0, title="Test", description="Test")
        created_ticket = in_memory_repository.create(ticket)

        comment = Comment(
            id=0,
            ticket_id=created_ticket.id,
            content="Test comment"
        )
        created_comment = in_memory_repository.add_comment(comment)

        assert created_comment.id > 0
        assert created_comment.ticket_id == created_ticket.id
        assert created_comment.content == "Test comment"

    def test_add_comment_assigns_id(self, in_memory_repository):
        """Cada comentário deve ter um ID único."""
        ticket = Ticket(id=0, title="Test", description="Test")
        created_ticket = in_memory_repository.create(ticket)

        comment1 = Comment(id=0, ticket_id=created_ticket.id, content="Comment 1")
        comment2 = Comment(id=0, ticket_id=created_ticket.id, content="Comment 2")

        c1 = in_memory_repository.add_comment(comment1)
        c2 = in_memory_repository.add_comment(comment2)

        assert c1.id != c2.id
        assert c1.id == 1
        assert c2.id == 2

    def test_add_comment_to_non_existent_ticket_raises_error(self, in_memory_repository):
        """Adicionar comentário a ticket inexistente deve falhar."""
        comment = Comment(id=0, ticket_id=999, content="Test")
        with pytest.raises(ValueError):
            in_memory_repository.add_comment(comment)

    def test_add_comment_none_raises_error(self, in_memory_repository):
        """Adicionar None como comentário deve falhar."""
        with pytest.raises(ValueError):
            in_memory_repository.add_comment(None)

    def test_add_comment_associates_with_ticket(self, in_memory_repository):
        """Comentário deve ser acessível através do ticket."""
        ticket = Ticket(id=0, title="Test", description="Test")
        created_ticket = in_memory_repository.create(ticket)

        comment = Comment(id=0, ticket_id=created_ticket.id, content="Test comment")
        in_memory_repository.add_comment(comment)

        retrieved = in_memory_repository.get_by_id(created_ticket.id)
        assert len(retrieved.comments) == 1
        assert retrieved.comments[0].content == "Test comment"

    def test_add_multiple_comments_to_same_ticket(self, in_memory_repository):
        """Ticket pode ter múltiplos comentários."""
        ticket = Ticket(id=0, title="Test", description="Test")
        created_ticket = in_memory_repository.create(ticket)

        for i in range(5):
            comment = Comment(
                id=0,
                ticket_id=created_ticket.id,
                content=f"Comment {i}"
            )
            in_memory_repository.add_comment(comment)

        retrieved = in_memory_repository.get_by_id(created_ticket.id)
        assert len(retrieved.comments) == 5


class TestInMemoryRepositoryEdgeCases:
    """Testes de casos extremos."""

    def test_repository_isolation(self):
        """Cada repositório deve ser isolado."""
        repo1 = InMemoryTicketRepository()
        repo2 = InMemoryTicketRepository()

        t1 = Ticket(id=0, title="Ticket 1", description="Desc 1")
        repo1.create(t1)

        tickets_repo2, _ = repo2.get_all()
        assert len(tickets_repo2) == 0

    def test_large_number_of_tickets(self, in_memory_repository):
        """Deve suportar grande número de tickets."""
        for i in range(1000):
            ticket = Ticket(id=0, title=f"Ticket {i}", description=f"Desc {i}")
            in_memory_repository.create(ticket)

        tickets, total = in_memory_repository.get_all()
        assert total == 1000

    def test_pagination_with_large_dataset(self, in_memory_repository):
        """Paginação deve funcionar com muitos dados."""
        for i in range(100):
            ticket = Ticket(id=0, title=f"Ticket {i}", description=f"Desc {i}")
            in_memory_repository.create(ticket)

        page1, total = in_memory_repository.get_all(page=1, size=25)
        page2, _ = in_memory_repository.get_all(page=2, size=25)
        page3, _ = in_memory_repository.get_all(page=3, size=25)
        page4, _ = in_memory_repository.get_all(page=4, size=25)

        assert len(page1) == 25
        assert len(page2) == 25
        assert len(page3) == 25
        assert len(page4) == 25
        assert total == 100
