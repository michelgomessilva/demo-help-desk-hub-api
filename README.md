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

## 📁 Estrutura do projeto

```
src/
├── main.py                               ← Ponto de entrada
├── api/
│   ├── routes/                           ← Apenas endpoints HTTP
│   │   ├── system_routes.py
│   │   ├── ticket_routes.py
│   │   └── categories_routes.py
│   └── schemas/                          ← Apenas validação Pydantic
│       ├── requests/
│       └── responses/
├── application/
│   └── ticket_service.py                 ← Lógica de negócio
├── domain/
│   └── tickets/
│       ├── enums.py                      ← Enumerações de domínio
│       ├── models.py                     ← Dataclasses puras
│       ├── exceptions.py                 ← Exceções de negócio
│       └── repositories.py               ← Interface (contrato)
└── infrastructure/
    ├── di/                               ← 🎯 Injeção de dependências
    │   ├── __init__.py
    │   └── dependencies.py               ← Dependências do FastAPI
    ├── database.py                       ← Configuração SQLAlchemy
    ├── models/
    │   └── ticket_orm.py                 ← Models ORM
    └── repositories/
        ├── in_memory_ticket_repository.py
        └── sqlalchemy_ticket_repository.py
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

## 📚 Documentação completa

Lê **[EXPLANATION.md](./EXPLANATION.md)** (40-50 min) para:

- Explicação detalhada de cada ficheiro
- Exemplos reais de SOLID aplicado
- Como evitar armadilhas comuns
- Roadmap de próximas funcionalidades

## 🚀 Próximos passos

Depois de compreender a arquitetura atual, evolui o projeto com:

1. **Autenticação (JWT)**
   - Adicionar tabela de users
   - Endpoint de login
   - Middleware de autenticação

2. **Testes**
   - Unit tests (mockar repositório)
   - Integration tests (testar com BD)
   - E2E tests (testar fluxo completo)

3. **Migrations com Alembic**
   - Melhor que `Base.metadata.create_all()`
   - Controle de versão do schema

4. **Docker + CI/CD**
   - Dockerfile para containerização
   - GitHub Actions para testes automáticos
   - Deploy automático

Vê **EXPLANATION.md** para um guia detalhado de cada passo.

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
