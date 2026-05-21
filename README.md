# HelpDesk Hub API

Uma API profissional e educativa para gerenciamento de chamados de suporte técnico, construída com **arquitetura em camadas**, **padrão Repository** e **princípios SOLID**.

## 🎯 O que é?

Este projeto demonstra como construir uma API REST moderna e escalável seguindo as melhores práticas de engenharia de software. É um projeto educativo que mostra:

- ✅ Separação clara de responsabilidades (camadas)
- ✅ Padrão Repository para inversão de dependência
- ✅ SOLID principles aplicados a código real
- ✅ Duas implementações de armazenamento (memória e PostgreSQL)
- ✅ Validação com Pydantic
- ✅ Documentação automática com FastAPI/Swagger
- ✅ Tratamento de exceções em camadas apropriadas
- ✅ Logging estruturado em JSON com Structlog

## 📋 Pré-requisitos

- **Python 3.11+**
- **PostgreSQL** (opcional, para Week 4)

## 🚀 Quick Start

### 1. Instalar dependências

```bash
uv sync
```

### 2. Rodar com armazenamento em memória (Week 2/3)

```bash
PYTHONPATH=src uvicorn src.main:app --reload
```

Abre [http://localhost:8000/docs](http://localhost:8000/docs) para a documentação Swagger.

### 3. Rodar com PostgreSQL (Week 4)

#### Configurar a base de dados

```bash
# Opção 1: Docker
docker run --name helpdesk-db \
  -e POSTGRES_PASSWORD=helpdesk_password \
  -p 5432:5432 \
  -d postgres

# Opção 2: Instalar localmente
# macOS: brew install postgresql@15
# Linux: sudo apt install postgresql
# Windows: https://www.postgresql.org/download/windows/

# Criar user e database
psql -U postgres
CREATE USER helpdesk_user WITH PASSWORD 'helpdesk_password';
CREATE DATABASE helpdesk_db OWNER helpdesk_user;
\q
```

#### Configurar variáveis de ambiente

```bash
cp .env.example .env
# Editar .env com a DATABASE_URL correta
# DATABASE_URL=postgresql://helpdesk_user:helpdesk_password@localhost:5432/helpdesk_db
```

#### Aplicar migrations com Alembic

```bash
# Aplicar todas as migrations até à versão mais recente
alembic upgrade head

# Ver histórico de migrations aplicadas
alembic history

# Ver status atual
alembic current
```

Isto criará as tabelas:
- `tickets` — com colunas: id, title, description, status, priority, category, created_at, assigned_to
- `comments` — com colunas: id, ticket_id, content, created_at
- `users` — com colunas: id, name, email, password_hash, role, is_active, created_at, telephone

#### Trocar para SQLAlchemy

Edita `src/api/routes/ticket_routes.py` e descomenta a secção **"SEMANA 4 - TROCAR REPOSITÓRIO"**:

```python
# Antes:
_repository = InMemoryTicketRepository()

# Depois:
from src.infrastructure.database import SessionLocal
from src.infrastructure.repositories.sqlalchemy_ticket_repository import SQLAlchemyTicketRepository

_repository = SQLAlchemyTicketRepository(SessionLocal())
```

#### Rodar a app

```bash
PYTHONPATH=src uvicorn src.main:app --reload
```

Abre [http://localhost:8000/docs](http://localhost:8000/docs) e testa os endpoints!

## 📡 Endpoints principais

### Tickets

| Método | Endpoint                              | Descrição                           |
|--------|---------------------------------------|-------------------------------------|
| `POST` | `/tickets`                            | Criar ticket                        |
| `GET`  | `/tickets`                            | Listar tickets                      |
| `GET`  | `/tickets?status=open&priority=high`  | Filtrar por status/prioridade       |
| `GET`  | `/tickets?page=1&size=10`             | Paginação                           |
| `GET`  | `/tickets/{id}`                       | Obter ticket específico             |
| `PATCH`| `/tickets/{id}`                       | Atualizar status/prioridade         |

### Comentários

| Método | Endpoint                 | Descrição            |
|--------|--------------------------|----------------------|
| `POST` | `/tickets/{id}/comments` | Adicionar comentário |

### Sistema

| Método | Endpoint     | Descrição                    |
|--------|--------------|------------------------------|
| `GET`  | `/`          | Info da API                  |
| `GET`  | `/health`    | Health check                 |
| `GET`  | `/categories`| Listar categorias de tickets |
| `GET`  | `/docs`      | Swagger UI                   |
| `GET`  | `/redoc`     | ReDoc documentação           |

## 🏛️ Arquitetura

```
┌─────────────────────────────────────────┐
│ API Layer                               │
│ (HTTP, JSON, Status Codes)              │
│ routes/ + schemas/                      │
├─────────────────────────────────────────┤
│ Application Layer                       │
│ (Lógica de Negócio)                     │
│ ticket_service.py                       │
├─────────────────────────────────────────┤
│ Domain Layer                            │
│ (Puro, sem HTTP/DB)                     │
│ models, enums, exceptions, interfaces   │
├─────────────────────────────────────────┤
│ Infrastructure Layer                    │
│ (Detalhes Técnicos)                     │
│ repositories, DI, database, ORM         │
└─────────────────────────────────────────┘
```

## 📊 Logging Estruturado

Este projeto implementa **logging estruturado em JSON** usando **Structlog**, permitindo rastrear eventos e diagnosticar problemas facilmente.

### Onde ficam os logs?

Os logs são salvos em `logs/app.jsonl` — um ficheiro JSONL (uma linha JSON por evento) que é mantido indefinidamente para análise posterior.

Cada linha é um evento completo:
```json
{"timestamp":"2024-01-15T10:30:45.123456","level":"info","event":"ticket_created_successfully","ticket_id":1,"title":"Login broken","user_id":5}
{"timestamp":"2024-01-15T10:31:12.654321","level":"warning","event":"ticket_not_found","ticket_id":999}
{"timestamp":"2024-01-15T10:31:45.987654","level":"error","event":"database_error","error":"Connection refused"}
```

### Como consultar logs?

**Últimos 10 logs em tempo real:**
```bash
tail -f logs/app.jsonl | jq .
```

**Filtrar por nível (apenas errors):**
```bash
grep '"level":"error"' logs/app.jsonl | jq .
```

**Filtrar por evento (ex: tickets criados):**
```bash
grep 'ticket_created_successfully' logs/app.jsonl | jq .
```

**Filtrar por user_id:**
```bash
grep '"user_id":5' logs/app.jsonl | jq .
```

**Ver apenas campo específico:**
```bash
cat logs/app.jsonl | jq '.ticket_id'
```

### Variável de ambiente

```env
LOG_LEVEL=DEBUG          # DEBUG, INFO (default), WARNING, ERROR
```

| Nível | O que mostra |
|-------|-------------|
| `DEBUG` | Todos os eventos, incluindo detalhes internos de operações |
| `INFO` (default) | Eventos importantes: criação, atualização, autenticação |
| `WARNING` | Apenas avisos e erros esperados (404, 400, etc) |
| `ERROR` | Apenas erros não esperados (exceções, falhas) |

### O que é logado?

**Middleware HTTP** — todas as requisições:
- Método (GET, POST, etc)
- Caminho (/tickets, /auth/login, etc)
- Status code (200, 404, 500, etc)
- Tempo de processamento (ms)
- IP do cliente
- User ID (se autenticado com JWT)

**Camada de Aplicação** — lógica de negócio:
- Criação/atualização de tickets
- Autenticação e login
- Validações e erros de negócio

**Banco de dados** — operações ORM:
- Inserts, updates, queries
- Relacionamentos

**Segurança** — JWT:
- Criação de tokens
- Verificação de tokens
- Extrações de claims

Lê **[EXPLANATION.md — Logging Estruturado](./EXPLANATION.md#logging-estruturado)** para detalhes completos sobre que eventos são emitidos em cada camada.

## 📁 Estrutura do projeto

```
.
├── alembic.ini                           ← Configuração do Alembic
├── migrations/                           ← 🎯 Migrações de banco de dados
│   ├── env.py                            ← Configuração do Alembic
│   ├── script.py.mako                    ← Template de migration
│   └── versions/                         ← Histórico de mudanças
│       ├── 1542ad98c7c7_create_initial_schema.py
│       ├── 59b2b3227eb5_create_users_table.py
│       ├── 05d6a98dc1c6_add_telephone_field_to_users.py
│       └── 69b887a5d772_add_assigned_to_field_to_tickets.py
├── src/
│   ├── main.py                           ← Ponto de entrada
│   ├── api/
│   │   ├── routes/                       ← Apenas endpoints HTTP
│   │   │   ├── system_routes.py
│   │   │   ├── ticket_routes.py
│   │   │   └── categories_routes.py
│   │   └── schemas/                      ← Apenas validação Pydantic
│   │       ├── requests/
│   │       └── responses/
│   ├── application/
│   │   └── ticket_service.py             ← Lógica de negócio
│   ├── domain/
│   │   └── tickets/
│   │       ├── enums.py                  ← Enumerações de domínio
│   │       ├── models.py                 ← Dataclasses puras
│   │       ├── exceptions.py             ← Exceções de negócio
│   │       └── repositories.py           ← Interface (contrato)
│   └── infrastructure/
│       ├── di/                           ← 🎯 Injeção de dependências
│       │   ├── __init__.py
│       │   └── dependencies.py           ← Dependências do FastAPI
│       ├── database.py                   ← Configuração SQLAlchemy
│       ├── models/
│       │   ├── ticket_orm.py             ← Models ORM (Tickets, Comments)
│       │   └── user_orm.py               ← Model ORM (Users)
│       └── repositories/
│           ├── in_memory_ticket_repository.py
│           └── sqlalchemy_ticket_repository.py
```

## 🎓 Conceitos-chave

### Padrão Repository

A interface `ITicketRepository` fica na camada `domain`. As implementações ficam na camada `infrastructure`.

Isto permite:

- ✅ Trocar implementações sem mexer no service
- ✅ Testar com mock repository
- ✅ Evoluir para diferentes bases de dados facilmente

### SOLID Principles

- **S** — Cada classe tem uma responsabilidade
- **O** — Aberto para extensão, fechado para modificação
- **L** — Substituição de subclasses sem quebrar o código
- **I** — Interfaces focadas no necessário
- **D** — Depender de abstrações, não de implementações

### DRY (Don't Repeat Yourself)

- `PaginatedResponse[T]` genérico para reutilização
- Conversões centralizadas entre modelos
- Validações reutilizáveis com Pydantic

### Alembic — Versionamento de Schema

O projeto usa **Alembic** para controlar as mudanças ao schema da base de dados.

**Por que Alembic?**
- ✅ Controlo de versão do banco (como git, mas para SQL)
- ✅ Rastrear quem mudou o quê e quando
- ✅ Fácil para revert (undo) de mudanças
- ✅ Geração automática de migrations

**Como adicionar uma coluna nova:**

1. Editar o model ORM:
```python
# src/infrastructure/models/ticket_orm.py
class TicketORM(Base):
    # ... campos existentes ...
    severity = Column(String(50), nullable=True)  # ← NOVA COLUNA
```

2. Gerar migration automática:
```bash
alembic revision --autogenerate -m "Add severity field to tickets"
```

3. Verificar `migrations/versions/xxx_add_severity_field_to_tickets.py`

4. Aplicar ao banco:
```bash
alembic upgrade head
```

**Comandos úteis:**
```bash
alembic current              # Ver versão atual
alembic history              # Ver histórico
alembic downgrade -1         # Reverter última mudança
alembic upgrade <revision>   # Ir para versão específica
```

Lê **[EXPLANATION.md — Alembic](./EXPLANATION.md#alembic--migrações-de-banco-de-dados)** para explicação completa.

## 📚 Documentação completa

Lê **[EXPLANATION.md](./EXPLANATION.md)** (50-60 min) para:

- Explicação detalhada de cada ficheiro
- Exemplos reais de SOLID aplicado
- Como evitar armadilhas comuns
- Sistema de logging estruturado
- Como adicionar logs a novos componentes
- Roadmap de próximas funcionalidades

## 🚀 Próximos passos

Depois de compreender a arquitetura atual, evolui o projeto com:

1. **✅ Alembic — Migrações de Banco de Dados (Já Implementado!)**
   - ✅ Alembic configurado (`alembic.ini` + `migrations/`)
   - ✅ 4 migrations criadas (schemas, users, telephone, assigned_to)
   - ✅ ORM models definidos (TicketORM, CommentORM, UserORM)
   - Próximo: Implementar SQLAlchemyTicketRepository completo e trocar repositório

2. **✅ Logging Estruturado com Structlog (Já Implementado!)**
   - ✅ Logging em JSON estruturado
   - ✅ Middleware HTTP que loga todas as requisições
   - ✅ Logs estruturados em todas as camadas
   - ✅ Ficheiro `logs/app.jsonl` para persistência
   - ✅ Variável `LOG_LEVEL` para controlar verbosidade
   - Próximo: Implementar rotação de logs para produção

3. **✅ Autenticação (JWT) (Já Implementado!)**
   - ✅ Tabela de users já existe (UserORM)
   - ✅ Endpoint de login implementado
   - ✅ Middleware de autenticação
   - ✅ Hash de senhas (bcrypt)

4. **Testes**
   - Unit tests (mockar repositório)
   - Integration tests (testar com BD real)
   - E2E tests (testar fluxo completo)

5. **Docker + CI/CD**
   - Dockerfile para containerização
   - docker-compose.yml para PostgreSQL + API
   - GitHub Actions para testes automáticos
   - Deploy automático

Vê **EXPLANATION.md** para um guia detalhado de cada passo (especialmente as seções sobre [Alembic](#alembic--migrações-de-banco-de-dados) e [Como Evoluir o Projeto](#como-evoluir-o-projeto)).

## 🧪 Exemplos de uso

### Criar um ticket

```bash
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Não consigo fazer login",
    "description": "A password está correta mas não entra",
    "priority": "high",
    "category": "access"
  }'
```

### Listar tickets com filtro

```bash
curl "http://localhost:8000/tickets?status=open&priority=high&page=1&size=10"
```

### Adicionar comentário

```bash
curl -X POST http://localhost:8000/tickets/1/comments \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Consegui resolver!"
  }'
```

## ⚙️ Variáveis de ambiente

Cria `.env` na raiz (copia `.env.example`):

```env
DATABASE_URL=postgresql://user:password@localhost:5432/helpdesk_db
ENVIRONMENT=development
LOG_LEVEL=info
```

## 🛠️ Desenvolvimento

### Instalar dependências extras

```bash
# Testes
uv add --dev pytest pytest-asyncio

# Linting
uv add --dev ruff black

# Type checking
uv add --dev mypy
```

### Rodar testes

```bash
PYTHONPATH=src pytest
```

### Format code

```bash
black src/
ruff check src/ --fix
```

## 📖 Leitura recomendada

- [Clean Architecture — Uncle Bob](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Repository Pattern — Martin Fowler](https://martinfowler.com/eaaCatalog/repository.html)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/)

## 📝 Dúvidas?

1. Lê **EXPLANATION.md** para entender a arquitetura
2. Procura no código — cada método tem comentários em português
3. Testa os endpoints no Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)

## 📄 Licença

Projeto educativo. Livre para usar e adaptar.

---

**Começaste aqui?** Lê primeiro [EXPLANATION.md](./EXPLANATION.md) para entender a arquitetura. Depois evolui com autenticação, testes e deploy.

Bom código! 🚀
