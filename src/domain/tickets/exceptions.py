"""
Exceções de domínio para a camada de negócio.

Estas exceções representam erros de lógica de negócio, nunca detalhes HTTP.
A camada API converte estas exceções em respostas HTTP apropriadas.

Por que existem aqui?
- O domínio nunca sabe ou importa detalhes de HTTP
- Permite reutilizar a mesma lógica de negócio em diferentes contextos
  (API REST, CLI, testes, etc.)
- Mantém a separação de responsabilidades entre camadas
"""


class TicketNotFoundError(Exception):
    """
    Lançada quando tentamos aceder a um ticket que não existe.

    Esta é uma exceção de negócio: significa que o utilizador tentou fazer
    algo com um ticket que não foi encontrado. A camada API converte isto
    numa resposta HTTP 404.

    Atributos:
        ticket_id: o ID do ticket que não foi encontrado
    """

    def __init__(self, ticket_id: int):
        self.ticket_id = ticket_id
        super().__init__(f"Ticket with ID {ticket_id} not found")
