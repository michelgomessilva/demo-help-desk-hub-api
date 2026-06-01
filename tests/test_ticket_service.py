"""
Testes unitários para TicketService.

Cobre:
- Criação de tickets
- Listagem e filtragem
- Busca por ID
- Atualização de status e prioridade
- Adição de comentários
- Paginação
- Validações e tratamento de erros
"""

import pytest
from src.application.ticket_service import TicketService
from src.domain.tickets.models import Ticket, Comment
from src.domain.tickets.enums import TicketStatus, TicketPriority, TicketCategory
from src.domain.tickets.exceptions import TicketNotFoundError


class TestCreateTicket:
    """Testes de criação de tickets."""

    def test_create_ticket_successfully(self, ticket_service, ticket_data):
        """Deve criar um ticket com sucesso."""
        ticket = ticket_service.create_ticket(
            title=ticket_data["title"],
            description=ticket_data["description"],
            priority=ticket_data["priority"],
            category=ticket_data["category"],
        )
        assert ticket.id > 0
        assert ticket.title == ticket_data["title"]
        assert ticket.description == ticket_data["description"]
        assert ticket.priority == ticket_data["priority"]
        assert ticket.category == ticket_data["category"]
        assert ticket.status == TicketStatus.OPEN

    def test_create_ticket_assigns_id(self, ticket_service):
        """Cada ticket criado deve ter um ID único."""
        ticket1 = ticket_service.create_ticket(
            title="Ticket 1",
            description="Description 1"
        )
        ticket2 = ticket_service.create_ticket(
            title="Ticket 2",
            description="Description 2"
        )
        assert ticket1.id != ticket2.id
        assert ticket1.id > 0
        assert ticket2.id > 0

    def test_create_ticket_defaults_to_open(self, ticket_service):
        """Novo ticket deve ter status OPEN por padrão."""
        ticket = ticket_service.create_ticket(
            title="New Ticket",
            description="Description"
        )
        assert ticket.status == TicketStatus.OPEN

    def test_create_ticket_defaults_to_medium_priority(self, ticket_service):
        """Novo ticket deve ter prioridade MEDIUM por padrão."""
        ticket = ticket_service.create_ticket(
            title="New Ticket",
            description="Description"
        )
        assert ticket.priority == TicketPriority.MEDIUM

    def test_create_ticket_defaults_to_software_category(self, ticket_service):
        """Novo ticket deve ter categoria SOFTWARE por padrão."""
        ticket = ticket_service.create_ticket(
            title="New Ticket",
            description="Description"
        )
        assert ticket.category == TicketCategory.SOFTWARE

    def test_create_ticket_with_empty_title_raises_error(self, ticket_service):
        """Não deve criar ticket com título vazio."""
        with pytest.raises(ValueError) as exc_info:
            ticket_service.create_ticket(
                title="",
                description="Some description"
            )
        assert "Title cannot be empty" in str(exc_info.value)

    def test_create_ticket_with_whitespace_title_raises_error(self, ticket_service):
        """Título com apenas espaços deve ser rejeitado."""
        with pytest.raises(ValueError):
            ticket_service.create_ticket(
                title="   ",
                description="Some description"
            )

    def test_create_ticket_with_empty_description_raises_error(self, ticket_service):
        """Não deve criar ticket com descrição vazia."""
        with pytest.raises(ValueError) as exc_info:
            ticket_service.create_ticket(
                title="Valid Title",
                description=""
            )
        assert "Description cannot be empty" in str(exc_info.value)

    def test_create_ticket_with_whitespace_description_raises_error(self, ticket_service):
        """Descrição com apenas espaços deve ser rejeitada."""
        with pytest.raises(ValueError):
            ticket_service.create_ticket(
                title="Valid Title",
                description="   "
            )

    def test_create_ticket_with_all_priorities(self, ticket_service):
        """Deve criar tickets com todas as prioridades."""
        for priority in TicketPriority:
            ticket = ticket_service.create_ticket(
                title=f"Ticket {priority.value}",
                description="Description",
                priority=priority
            )
            assert ticket.priority == priority

    def test_create_ticket_with_all_categories(self, ticket_service):
        """Deve criar tickets com todas as categorias."""
        for category in TicketCategory:
            ticket = ticket_service.create_ticket(
                title=f"Ticket {category.value}",
                description="Description",
                category=category
            )
            assert ticket.category == category


class TestListTickets:
    """Testes de listagem de tickets."""

    def test_list_empty_repository(self, ticket_service):
        """Listar tickets de repositório vazio deve retornar lista vazia."""
        tickets, total = ticket_service.list_tickets()
        assert tickets == []
        assert total == 0

    def test_list_tickets_returns_tuple(self, ticket_service, created_ticket):
        """list_tickets deve retornar uma tupla (tickets, total)."""
        result = ticket_service.list_tickets()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_list_all_tickets(self, ticket_service, create_multiple_tickets):
        """Deve listar todos os tickets."""
        create_multiple_tickets(5)
        tickets, total = ticket_service.list_tickets()
        assert len(tickets) == 5
        assert total == 5

    def test_list_tickets_default_pagination(self, ticket_service, create_multiple_tickets):
        """Paginação padrão deve ser page=1, size=10."""
        create_multiple_tickets(5)
        tickets, total = ticket_service.list_tickets()
        assert len(tickets) == 5
        assert total == 5

    def test_list_tickets_with_pagination(self, ticket_service, create_multiple_tickets):
        """Deve suportar paginação."""
        create_multiple_tickets(25)
        page1, total = ticket_service.list_tickets(page=1, size=10)
        page2, _ = ticket_service.list_tickets(page=2, size=10)
        assert len(page1) == 10
        assert len(page2) == 10
        assert total == 25
        assert page1[0].id != page2[0].id

    def test_list_tickets_last_page_partial(self, ticket_service, create_multiple_tickets):
        """Última página pode ter menos items que page size."""
        create_multiple_tickets(25)
        page3, total = ticket_service.list_tickets(page=3, size=10)
        assert len(page3) == 5
        assert total == 25

    def test_list_tickets_page_out_of_range(self, ticket_service, create_multiple_tickets):
        """Página além do range deve retornar lista vazia."""
        create_multiple_tickets(5)
        tickets, total = ticket_service.list_tickets(page=10, size=10)
        assert tickets == []
        assert total == 5

    def test_list_tickets_invalid_page_defaults_to_1(self, ticket_service, created_ticket):
        """Página < 1 deve ser corrigida para 1."""
        tickets, _ = ticket_service.list_tickets(page=0, size=10)
        assert len(tickets) > 0

    def test_list_tickets_invalid_size_defaults_to_10(self, ticket_service, created_ticket):
        """Size inválido deve ser corrigido para 10."""
        tickets, _ = ticket_service.list_tickets(page=1, size=-1)
        assert len(tickets) > 0

    def test_list_tickets_filter_by_status(self, ticket_service):
        """Deve filtrar tickets por status."""
        # Criar um ticket e atualizar seu status
        ticket = ticket_service.create_ticket("Title", "Description")
        ticket_service.update_ticket(ticket.id, status=TicketStatus.CLOSED)

        # Listar apenas tickets fechados
        closed_tickets, total = ticket_service.list_tickets(status=TicketStatus.CLOSED)
        assert len(closed_tickets) == 1
        assert closed_tickets[0].status == TicketStatus.CLOSED
        assert total == 1

    def test_list_tickets_filter_by_priority(self, ticket_service):
        """Deve filtrar tickets por prioridade."""
        ticket_service.create_ticket("Title 1", "Desc", priority=TicketPriority.HIGH)
        ticket_service.create_ticket("Title 2", "Desc", priority=TicketPriority.LOW)

        high_tickets, total = ticket_service.list_tickets(priority=TicketPriority.HIGH)
        assert len(high_tickets) == 1
        assert total == 1

    def test_list_tickets_filter_by_category(self, ticket_service):
        """Deve filtrar tickets por categoria."""
        ticket_service.create_ticket("Title 1", "Desc", category=TicketCategory.HARDWARE)
        ticket_service.create_ticket("Title 2", "Desc", category=TicketCategory.SOFTWARE)

        hw_tickets, total = ticket_service.list_tickets(category=TicketCategory.HARDWARE)
        assert len(hw_tickets) == 1
        assert total == 1

    def test_list_tickets_multiple_filters(self, ticket_service):
        """Deve filtrar com múltiplos critérios simultaneamente."""
        # Criar tickets variados
        t1 = ticket_service.create_ticket(
            "Title 1", "Desc",
            priority=TicketPriority.HIGH,
            category=TicketCategory.HARDWARE
        )
        t2 = ticket_service.create_ticket(
            "Title 2", "Desc",
            priority=TicketPriority.HIGH,
            category=TicketCategory.SOFTWARE
        )

        # Filtrar por HIGH priority E HARDWARE category
        tickets, total = ticket_service.list_tickets(
            priority=TicketPriority.HIGH,
            category=TicketCategory.HARDWARE
        )
        assert len(tickets) == 1
        assert tickets[0].id == t1.id


class TestGetTicket:
    """Testes de busca de um ticket específico."""

    def test_get_ticket_successfully(self, ticket_service, created_ticket):
        """Deve retornar um ticket existente."""
        retrieved = ticket_service.get_ticket(created_ticket.id)
        assert retrieved.id == created_ticket.id
        assert retrieved.title == created_ticket.title

    def test_get_non_existent_ticket_raises_error(self, ticket_service):
        """Buscar ticket inexistente deve lançar erro."""
        with pytest.raises(TicketNotFoundError):
            ticket_service.get_ticket(999)

    def test_get_ticket_preserves_all_fields(self, ticket_service):
        """Ticket retornado deve ter todos os campos."""
        ticket = ticket_service.create_ticket(
            title="Test Title",
            description="Test Description",
            priority=TicketPriority.HIGH,
            category=TicketCategory.HARDWARE
        )
        retrieved = ticket_service.get_ticket(ticket.id)
        assert retrieved.title == "Test Title"
        assert retrieved.description == "Test Description"
        assert retrieved.priority == TicketPriority.HIGH
        assert retrieved.category == TicketCategory.HARDWARE


class TestUpdateTicket:
    """Testes de atualização de tickets."""

    def test_update_ticket_status(self, ticket_service, created_ticket):
        """Deve atualizar o status de um ticket."""
        updated = ticket_service.update_ticket(
            created_ticket.id,
            status=TicketStatus.IN_PROGRESS
        )
        assert updated.status == TicketStatus.IN_PROGRESS

    def test_update_ticket_priority(self, ticket_service, created_ticket):
        """Deve atualizar a prioridade de um ticket."""
        updated = ticket_service.update_ticket(
            created_ticket.id,
            priority=TicketPriority.HIGH
        )
        assert updated.priority == TicketPriority.HIGH

    def test_update_ticket_both_fields(self, ticket_service, created_ticket):
        """Deve atualizar status e prioridade simultaneamente."""
        updated = ticket_service.update_ticket(
            created_ticket.id,
            status=TicketStatus.CLOSED,
            priority=TicketPriority.LOW
        )
        assert updated.status == TicketStatus.CLOSED
        assert updated.priority == TicketPriority.LOW

    def test_update_ticket_preserves_other_fields(self, ticket_service, created_ticket):
        """Atualizar não deve alterar outros campos."""
        original_title = created_ticket.title
        original_category = created_ticket.category

        ticket_service.update_ticket(
            created_ticket.id,
            status=TicketStatus.CLOSED
        )

        retrieved = ticket_service.get_ticket(created_ticket.id)
        assert retrieved.title == original_title
        assert retrieved.category == original_category

    def test_update_non_existent_ticket_raises_error(self, ticket_service):
        """Atualizar ticket inexistente deve lançar erro."""
        with pytest.raises(TicketNotFoundError):
            ticket_service.update_ticket(999, status=TicketStatus.CLOSED)

    def test_update_ticket_with_none_values_ignored(self, ticket_service, created_ticket):
        """None em parâmetros não deve alterar os campos."""
        ticket_service.update_ticket(created_ticket.id, status=TicketStatus.IN_PROGRESS)
        updated = ticket_service.update_ticket(created_ticket.id, status=None, priority=None)

        retrieved = ticket_service.get_ticket(created_ticket.id)
        assert retrieved.status == TicketStatus.IN_PROGRESS


class TestAddComment:
    """Testes de adição de comentários."""

    def test_add_comment_successfully(self, ticket_service, created_ticket, comment_data):
        """Deve adicionar um comentário a um ticket."""
        comment = ticket_service.add_comment(
            created_ticket.id,
            comment_data["content"]
        )
        assert comment.id > 0
        assert comment.ticket_id == created_ticket.id
        assert comment.content == comment_data["content"]

    def test_add_comment_assigns_id(self, ticket_service, created_ticket):
        """Cada comentário deve ter um ID único."""
        comment1 = ticket_service.add_comment(created_ticket.id, "Comment 1")
        comment2 = ticket_service.add_comment(created_ticket.id, "Comment 2")
        assert comment1.id != comment2.id

    def test_add_comment_to_non_existent_ticket_raises_error(self, ticket_service):
        """Adicionar comentário a ticket inexistente deve falhar."""
        with pytest.raises(TicketNotFoundError):
            ticket_service.add_comment(999, "Some comment")

    def test_add_comment_with_empty_content_raises_error(self, ticket_service, created_ticket):
        """Comentário vazio deve ser rejeitado."""
        with pytest.raises(ValueError):
            ticket_service.add_comment(created_ticket.id, "")

    def test_add_comment_with_whitespace_content_raises_error(self, ticket_service, created_ticket):
        """Comentário com apenas espaços deve ser rejeitado."""
        with pytest.raises(ValueError):
            ticket_service.add_comment(created_ticket.id, "   ")

    def test_add_multiple_comments(self, ticket_service, created_ticket):
        """Deve permitir múltiplos comentários no mesmo ticket."""
        comment1 = ticket_service.add_comment(created_ticket.id, "First comment")
        comment2 = ticket_service.add_comment(created_ticket.id, "Second comment")

        assert comment1.id != comment2.id
        assert comment1.ticket_id == comment2.ticket_id

    def test_comments_associated_with_ticket(self, ticket_service, created_ticket):
        """Comentários devem ser acessíveis através do ticket."""
        ticket_service.add_comment(created_ticket.id, "Comment 1")
        ticket_service.add_comment(created_ticket.id, "Comment 2")

        retrieved = ticket_service.get_ticket(created_ticket.id)
        assert len(retrieved.comments) == 2

    def test_add_comment_with_long_content(self, ticket_service, created_ticket):
        """Deve suportar comentários longos."""
        long_comment = "a" * 5000
        comment = ticket_service.add_comment(created_ticket.id, long_comment)
        assert comment.content == long_comment


class TestTicketServiceEdgeCases:
    """Testes de casos extremos."""

    def test_create_many_tickets_performance(self, ticket_service):
        """Deve criar muitos tickets sem problemas."""
        for i in range(100):
            ticket = ticket_service.create_ticket(
                title=f"Ticket {i}",
                description=f"Description {i}"
            )
            assert ticket.id == i + 1

    def test_update_ticket_multiple_times(self, ticket_service, created_ticket):
        """Deve permitir atualizar um ticket múltiplas vezes."""
        ticket_id = created_ticket.id

        for i, status in enumerate(TicketStatus):
            updated = ticket_service.update_ticket(ticket_id, status=status)
            assert updated.status == status

    def test_ticket_with_special_characters(self, ticket_service):
        """Deve suportar caracteres especiais em título e descrição."""
        ticket = ticket_service.create_ticket(
            title="Ticket com Ç€ñtûs!#@$%",
            description="Descrição com émojis 😀🔧🐛"
        )
        retrieved = ticket_service.get_ticket(ticket.id)
        assert "Ç€ñtûs" in retrieved.title
        assert "émojis" in retrieved.description
