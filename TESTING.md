# Guia de Testes - HelpDesk Hub API

## Estrutura de Testes

O projeto segue uma estrutura de testes bem organizada:

```
tests/
├── __init__.py                      # Inicialização do pacote
├── conftest.py                      # Fixtures globais do pytest
├── test_auth_service.py             # Testes do AuthService
├── test_ticket_service.py           # Testes do TicketService
├── test_in_memory_repository.py     # Testes do InMemoryTicketRepository
├── test_api_routes.py               # Testes das rotas HTTP
└── test_domain.py                   # Testes dos modelos de domínio
```

## Instalação

Este projeto usa **uv** como gestor de dependências. Sempre use `uv` em vez de `pip`.

### Instalar dependências de teste

```bash
# Adicionar como dependências de desenvolvimento
uv add --dev pytest pytest-asyncio httpx

# Ou instalar todas as dependências do projeto (incluindo dev)
uv sync --all-extras
```

## Executar Testes

### Todos os testes
```bash
uv run pytest
```

### Com saída verbosa
```bash
uv run pytest -v
```

### Testes de um arquivo específico
```bash
uv run pytest tests/test_auth_service.py
```

### Testes de uma classe específica
```bash
uv run pytest tests/test_auth_service.py::TestPasswordHashing
```

### Testes de um método específico
```bash
uv run pytest tests/test_auth_service.py::TestPasswordHashing::test_hash_password_returns_string
```

### Testes com cobertura de código
```bash
uv add --dev pytest-cov
uv run pytest --cov=src --cov-report=html
```

### Apenas testes rápidos (excluindo lentos)
```bash
uv run pytest -m "not slow"
```

### Parar no primeiro erro
```bash
uv run pytest -x
```

### Último teste que falhou
```bash
uv run pytest --lf
```

## Estrutura de Testes

### Fixtures

O arquivo `conftest.py` fornece fixtures reutilizáveis:

#### Database
- `test_db_session`: Sessão de banco de dados SQLite em memória
- `test_database_url`: URL de banco de dados de teste
- `test_engine`: Motor de banco de dados SQLAlchemy

#### Repositórios
- `in_memory_repository`: Repositório em memória limpo

#### Serviços
- `auth_service`: AuthService configurado para testes
- `ticket_service`: TicketService com repositório em memória

#### API
- `app`: Aplicação FastAPI para testes
- `client`: Cliente HTTP TestClient para requisições

#### Dados de Teste
- `test_user_data`: Dados de usuário para testes
- `test_admin_data`: Dados de admin para testes
- `registered_user`: Usuário já registrado no banco
- `ticket_data`: Dados de ticket para testes
- `high_priority_ticket_data`: Dados de ticket urgente
- `created_ticket`: Ticket já criado no repositório
- `comment_data`: Dados de comentário

#### Helpers
- `create_multiple_tickets`: Factory para criar múltiplos tickets

### Cobertura de Testes

#### test_auth_service.py
- ✅ Hash de senhas (bcrypt)
- ✅ Verificação de senhas
- ✅ Registro de usuários
- ✅ Autenticação
- ✅ Validação de emails únicos
- ✅ Caracteres especiais e Unicode

#### test_ticket_service.py
- ✅ Criação de tickets
- ✅ Listagem e paginação
- ✅ Filtragem por status, prioridade, categoria
- ✅ Busca por ID
- ✅ Atualização de tickets
- ✅ Adição de comentários
- ✅ Validações e erros

#### test_in_memory_repository.py
- ✅ Operações CRUD
- ✅ Armazenamento em memória
- ✅ Paginação
- ✅ Filtros
- ✅ Gerenciamento de comentários
- ✅ Performance com muitos dados

#### test_api_routes.py
- ✅ Rotas de sistema (/, /health)
- ✅ Autenticação (register, login)
- ✅ Tickets (create, list, get, update)
- ✅ Comentários
- ✅ Categorias
- ✅ Status codes HTTP
- ✅ Validação de respostas

#### test_domain.py
- ✅ Modelos (Ticket, Comment)
- ✅ Enums (Status, Priority, Category)
- ✅ Exceções (TicketNotFoundError)
- ✅ Relacionamentos

## Convenções de Testes

### Nomeação

```python
# Classe de teste agrupa testes relacionados
class TestCreateTicket:
    # Método de teste descreve o que testa
    def test_create_ticket_successfully(self):
        pass
```

### Estrutura (AAA)

```python
def test_example(self, fixture):
    # Arrange - Preparar dados
    data = {"title": "Test"}

    # Act - Executar ação
    result = service.create(data)

    # Assert - Verificar resultado
    assert result.id > 0
```

### Fixtures

```python
# Fixture fixa um comportamento
@pytest.fixture
def auth_service(test_db_session):
    return AuthService(test_db_session)

# Usar a fixture como parâmetro
def test_example(self, auth_service):
    pass
```

### Exceções

```python
# Testar que uma exceção é lançada
def test_error(self, service):
    with pytest.raises(ValueError):
        service.invalid_operation()
```

## Integração Contínua

Para usar testes em CI/CD com uv:

```yaml
# GitHub Actions example
- name: Install uv
  uses: astral-sh/setup-uv@v3

- name: Install dependencies
  run: uv sync --all-extras

- name: Run tests
  run: uv run pytest --cov=src

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Boas Práticas

1. **Isolamento**: Cada teste deve ser independente
2. **Clareza**: Nome descritivo e código legível
3. **Rapidez**: Testes devem rodar rápido (sem I/O real)
4. **Completude**: Cobrir casos normais e edge cases
5. **DRY**: Reutilizar fixtures em vez de duplicar setup
6. **uv**: Sempre use `uv run` para executar comandos do projeto

## Troubleshooting

### Testes não são descobertos
```bash
# Verificar convenção de nomenclatura
# - Arquivos: test_*.py ou *_test.py
# - Classes: Test*
# - Métodos: test_*
uv run pytest --collect-only
```

### ImportError em testes
```bash
# uv gere automaticamente o PYTHONPATH ao executar
uv run pytest
```

### Testes lentos
```bash
# Encontrar testes lentos
uv run pytest --durations=10
```

## Próximas Etapas

- [ ] Adicionar testes para SQLAlchemy Repository
- [ ] Adicionar testes para JWT Handler
- [ ] Adicionar testes de middleware
- [ ] Adicionar testes de integração com banco PostgreSQL
- [ ] Adicionar testes de performance
- [ ] Configurar CI/CD com GitHub Actions
