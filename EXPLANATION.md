# EXPLANATION.md — Guia Completo da HelpDesk Hub API

Bem-vindo a este documento! Se nunca viste este projeto, lê isto do início ao fim. Vamos explorar a arquitetura, o código, os princípios e como evoluir a partir daqui.

---

## Índice

1. [Introdução](#introdução)
2. [O que é um HelpDesk](#o-que-é-um-helpdesk)
3. [Arquitetura em Camadas](#arquitetura-em-camadas)
4. [Explicação Ficheiro a Ficheiro](#explicação-ficheiro-a-ficheiro)
5. [Modelos ORM e Base de Dados](#modelos-orm-e-base-de-dados)
6. [Alembic — Migrações de Banco de Dados](#alembic--migrações-de-banco-de-dados)
7. [Princípios SOLID Aplicados](#princípios-solid-aplicados)
8. [DRY — Don't Repeat Yourself](#dry--dont-repeat-yourself)
9. [Guard Clauses](#guard-clauses)
10. [Padrão Repository](#padrão-repository)
11. [Fluxo de Uma Requisição](#fluxo-de-uma-requisição)
12. [Como Evoluir o Projeto](#como-evoluir-o-projeto)

---

## Introdução

Este é um projeto educativo para aprender a construir APIs REST profissionais em Python.

**Para quem é isto?**
- Alguém que nunca construiu uma API REST
- Alguém que quer aprender boas práticas de arquitetura
- Alguém que quer entender como separar responsabilidades no código

**O que vais aprender?**
- ✅ Arquitetura em camadas (Clean Architecture)
- ✅ Padrão Repository
- ✅ Princípios SOLID
- ✅ Injeção de Dependência
- ✅ Separação de conceitos
- ✅ Como fazer código profissional e mantível

**Tempo estimado para ler:** 30-40 minutos

---

## O que é um HelpDesk?

Um HelpDesk é um sistema que **recebe e gere pedidos de suporte** dos utilizadores.

### Exemplo real

```
Utilizador: "Não consigo fazer login na aplicação"
    ↓
Sistema: Cria um Ticket (número 1234)
    ↓
Suporte: "Estou a trabalhar nisso"
    ↓
Sistema: Adiciona um Comentário ao Ticket
    ↓
Suporte: Muda o status para "In Progress"
    ↓
...tempo passa...
    ↓
Suporte: "Resolvido! Era um cookie antigo"
    ↓
Sistema: Muda o status para "Resolved"
    ↓
Utilizador: Vê que foi resolvido
```

### Entidades principais

**Ticket** — Um pedido de suporte
- ID único
- Título e descrição
- Status: aberto, em progresso, resolvido, fechado
- Prioridade: baixa, média, alta, urgente
- Categoria: acesso, hardware, software, rede
- Data de criação
- Comentários associados

**Comentário** — Uma anotação num ticket
- ID único
- Conteúdo (texto)
- Ticket ao qual pertence
- Data de criação

**Categoria** — Um tipo de problema (predefinido)
- Não tem CRUD completo (é um enum)

---

## Arquitetura em Camadas

Esta API segue o padrão **Clean Architecture**, também conhecido como **Arquitetura em Camadas**.

### Diagrama visual

```
┌─────────────────────────────────────┐
│          API / HTTP LAYER           │
│   (Routes, Status Codes, JSON)      │
├─────────────────────────────────────┤
│      APPLICATION LAYER              │
│   (Lógica de Negócio, Validações)   │
├─────────────────────────────────────┤
│       DOMAIN LAYER                  │
│  (Interfaces, Modelos, Exceções)    │
├─────────────────────────────────────┤
│    INFRASTRUCTURE LAYER             │
│  (Implementações: Memory, DB, etc)  │
└─────────────────────────────────────┘
```

### Fluxo de uma requisição

```
Browser/Cliente
     ↓
[HTTP POST /tickets]
     ↓
API Layer (Routes)
  - Recebe JSON
  - Valida com Pydantic
  - Chama Service
     ↓
Application Layer (Service)
  - Lógica de negócio
  - Validações
  - Chama Repository
     ↓
Domain Layer (Interface)
  - Define o contrato
     ↓
Infrastructure Layer (Implementação)
  - Guarda no repositório (memória/banco)
     ↓
Resposta volta para cima
     ↓
JSON retornado ao cliente
```

### Por que camadas?

| Razão | Benefício |
|-------|----------|
| **Separação de Conceitos** | Cada camada faz uma coisa bem |
| **Testabilidade** | Podes testar cada camada isoladamente |
| **Reutilização** | O service pode ser usado em CLI, webhooks, etc |
| **Flexibilidade** | Trocar implementações sem afetar lógica |
| **Manutenibilidade** | Código organizado é fácil de perceber |

---

## Explicação Ficheiro a Ficheiro

### `src/domain/tickets/models.py` — Entidades de domínio

**O que é?**
Define as classes que representam os conceitos do negócio: Ticket e Comment.

**Por que existe?**
Preciso de representar os dados de uma forma que o código de negócio entenda. Não são entidades do banco de dados (aquelas ficam na infrastructure), são entidades puras.

**Exemplo:**

```python
@dataclass
class Ticket:
    id: int
    title: str
    description: str
    status: TicketStatus = TicketStatus.OPEN  # Padrão
    priority: TicketPriority = TicketPriority.MEDIUM
    category: TicketCategory = TicketCategory.SOFTWARE
    created_at: datetime = field(default_factory=datetime.now)
    comments: list[Comment] = field(default_factory=list)
```

**Características:**
- Usa `@dataclass` — geração automática de `__init__`, `__repr__`, etc
- Atributos têm valores padrão — não é obrigatório fornecer tudo
- `comments` é uma lista vazia por padrão — facilita trabalhar com o ticket

**Sem este ficheiro, o que acontecia?**
- O service não saberia que estrutura usar
- Haveria confusão entre dados de HTTP e dados de negócio
- Código menos claro

---

### `src/domain/tickets/exceptions.py` — Exceções de negócio

**O que é?**
Define as exceções que o domínio levanta (erros de negócio, não de HTTP).

**Por que existe?**
O service precisa de comunicar que algo correu mal no negócio, sem saber de HTTP.

```python
class TicketNotFoundError(Exception):
    """Ticket não existe — exceção de negócio."""
    def __init__(self, ticket_id: int):
        self.ticket_id = ticket_id
        super().__init__(f"Ticket with ID {ticket_id} not found")
```

**Fluxo:**
```
Service levanta TicketNotFoundError("Ticket 999 not found")
     ↓
Routes captura e converte em HTTPException(404)
     ↓
FastAPI converte em resposta JSON com status 404
```

**Sem este ficheiro, o que acontecia?**
- Service teria que importar FastAPI e HTTPException (acoplamento!)
- Service não poderia ser reutilizado em CLI ou outros contextos
- Camadas ficariam acopladas

---

### `src/domain/tickets/repositories.py` — Interface

**O que é?**
Define o contrato que qualquer repositório deve cumprir.

**Por que existe?**
Permite trocar implementações (memória ↔ banco de dados) sem afetar o code.

```python
class ITicketRepository(ABC):
    """Interface que qualquer repositório deve implementar."""
    
    @abstractmethod
    def create(self, ticket: Ticket) -> Ticket:
        """Cria um novo ticket."""
        pass

    @abstractmethod
    def get_all(self, status, priority, category, page, size) -> tuple[list[Ticket], int]:
        """Lista tickets com filtros e retorna (items, total)."""
        pass

    # ... mais métodos
```

**Benefício:**
```
Service depends on ITicketRepository (interface)
        ↓
        ├─→ InMemoryTicketRepository (Semana 2)
        └─→ SQLAlchemyTicketRepository (Semana 4)

Service não sabe qual implementação está a usar!
```

**Sem este ficheiro, o que acontecia?**
- Service teria que conhecer detalhes de como guardar (acoplamento)
- Não poderias trocar implementações sem mudar o service
- Testes seriam complicados (não poderias mockar o repositório)

---

### `src/infrastructure/repositories/in_memory_ticket_repository.py` — Implementação

**O que é?**
Implementa a interface ITicketRepository guardando dados num dicionário Python.

**Por que existe?**
Permite desenvolver e testar sem precisar de banco de dados configurado.

```python
class InMemoryTicketRepository(ITicketRepository):
    def __init__(self):
        self._tickets: dict[int, Ticket] = {}
        self._next_id = 1

    def create(self, ticket: Ticket) -> Ticket:
        # Atribui ID e guarda
        ticket.id = self._next_id
        self._tickets[ticket.id] = ticket
        self._next_id += 1
        return ticket

    def get_all(self, status, priority, category, page, size):
        # Filtra, pagina e retorna (items, total)
        results = list(self._tickets.values())
        if status:
            results = [t for t in results if t.status == status]
        # ... mais filtros
        skip = (page - 1) * size
        return (results[skip : skip + size], len(results))
```

**Características:**
- Atributos privados com `_` — não mexas diretamente
- Guard Clauses — validações no início
- Retorna `tuple[list, total]` — cliente sabe quantas páginas existem

**Semana 4:**
Trocaremos isto por `SQLAlchemyTicketRepository` e o resto do código não muda.

---

### `src/application/ticket_service.py` — Lógica de negócio

**O que é?**
Orquestra as operações com tickets. Aqui fica a lógica que não é HTTP, nem DB.

**Por que existe?**
Centraliza a lógica e permite reutilizar em diferentes contextos (API, CLI, scripts).

```python
class TicketService:
    def __init__(self, repository: ITicketRepository):
        # Injeção de dependência — não criamos o repositório aqui
        self._repository = repository

    def create_ticket(self, title, description, priority, category) -> Ticket:
        # Guard Clause — validar no início
        if not title or not title.strip():
            raise ValueError("Title cannot be empty")

        # Criar modelo de domínio
        ticket = Ticket(id=0, title=title, description=description, ...)

        # Guardar usando repositório (não sabemos como)
        return self._repository.create(ticket)

    def get_ticket(self, ticket_id: int) -> Ticket:
        # Guard Clause
        ticket = self._repository.get_by_id(ticket_id)
        if not ticket:
            raise TicketNotFoundError(ticket_id)  # Exceção de negócio
        return ticket
```

**Características:**
- Não importa nada de FastAPI
- Levanta exceções de domínio (TicketNotFoundError)
- Depende de interface, não de implementação (ITicketRepository)

**Sem este ficheiro, o que acontecia?**
- Lógica ficaria nas rotas (misturado com HTTP)
- Não poderias testar sem fazer requisições HTTP
- Não poderias reutilizar em CLI

---

### `src/infrastructure/di/dependencies.py` — Injeção de Dependências

**O que é?**
Centraliza toda a configuração de dependências do FastAPI em um único lugar.

**Por que existe?**
- Infrastructure Layer = detalhes técnicos (FastAPI, SQLAlchemy, etc.)
- API Layer = apenas HTTP (rotas + schemas)
- Mantém cada camada com sua responsabilidade clara

```python
from fastapi import Depends
from src.application.ticket_service import TicketService
from src.domain.tickets.repositories import ITicketRepository
from src.infrastructure.repositories.in_memory_ticket_repository import InMemoryTicketRepository

def get_repository() -> ITicketRepository:
    """Fornece o repositório de tickets."""
    return InMemoryTicketRepository()

def get_service(repository: ITicketRepository = Depends(get_repository)) -> TicketService:
    """Fornece o serviço de tickets."""
    return TicketService(repository)
```

**Benefícios:**

- ✅ **SRP** — dependências num único lugar
- ✅ **Manutenção** — trocar repositório aqui (Semana 4)
- ✅ **Reutilização** — múltiplas rotas usam a mesma injeção
- ✅ **Testes** — injetar mocks facilmente

**SEMANA 4 — Trocar para PostgreSQL:**
Apenas alterar em `get_repository()`:
```python
def get_repository() -> ITicketRepository:
    from src.infrastructure.database import SessionLocal
    from src.infrastructure.repositories.sqlalchemy_ticket_repository import SQLAlchemyTicketRepository
    return SQLAlchemyTicketRepository(SessionLocal())
```

Nenhuma outra mudança em nenhum outro ficheiro! 🎯

---

### `src/api/routes/ticket_routes.py` — Endpoints HTTP

**O que é?**
Define as rotas HTTP e como convertem HTTP em chamadas de negócio.

**Por que existe?**
Separa HTTP (detalhes técnicos) da lógica (domínio).

```python
from fastapi import APIRouter, HTTPException, Depends
from src.infrastructure.di.dependencies import get_service

router = APIRouter(prefix="/tickets", tags=["Tickets"])

@router.post("/", response_model=TicketResponse, status_code=201)
def create_ticket(
    request: CreateTicketRequest,
    service: TicketService = Depends(get_service),
) -> TicketResponse:
    """POST /tickets — Criar ticket."""
    ticket = service.create_ticket(
        title=request.title,
        description=request.description,
        priority=request.priority,
        category=request.category,
    )
    return ticket  # FastAPI converte em JSON

@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: int,
    service: TicketService = Depends(get_service),
) -> TicketResponse:
    """GET /tickets/5 — Obter ticket."""
    try:
        return service.get_ticket(ticket_id)
    except TicketNotFoundError as e:
        # Converter exceção de negócio em HTTP 404
        raise HTTPException(status_code=404, detail=str(e))
```

**Responsabilidades:**

1. Receber HTTP (query params, path, body)
2. Validar com Pydantic
3. Injetar dependências via `Depends()`
4. Chamar service
5. Capturar exceções de negócio
6. Converter em HTTP (status codes, JSON)

**Sem este ficheiro, o que acontecia?**
- Service estaria acoplado a HTTP
- Não poderias trocar FastAPI por outro framework
- Código misturado: HTTP + lógica

**O que é `Depends(get_service)`?**
- FastAPI chama `get_service()` automaticamente
- FastAPI chama `get_repository()` automaticamente (via dependência)
- Injeta o service na função da rota
- Permite trocar implementações sem tocar nas rotas

---

### `src/api/schemas/` — Validação e formato

**Request schemas** (input)
```python
class CreateTicketRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    priority: TicketPriority = TicketPriority.MEDIUM
    category: TicketCategory = TicketCategory.SOFTWARE
```

**Pydantic faz:**
- ✅ Valida tipos (se `title` é string)
- ✅ Valida ranges (min_length, max_length)
- ✅ Rejeita campos desconhecidos
- ✅ Converte valores (string "high" → enum HIGH)
- ✅ Gera documentação no Swagger

**Response schemas** (output)
```python
class TicketResponse(BaseModel):
    id: int
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    category: TicketCategory
    created_at: datetime

    class Config:
        from_attributes = True  # Compatível com ORM
```

**Genérico reutilizável**
```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def from_data(cls, items, total, page, size):
        pages = math.ceil(total / size)
        return cls(items=items, total=total, page=page, size=size, pages=pages)
```

---

### `src/main.py` — Aplicação principal

**O que é?**
Factory function que cria e configura a aplicação FastAPI.

**Por que existe?**
Centraliza a configuração e permite criar a app em diferentes contextos.

```python
def create_app() -> FastAPI:
    """Cria a aplicação."""
    app = FastAPI(
        title="HelpDesk Hub API",
        description="...",
        version="1.0.0",
    )
    # Registar routers
    app.include_router(system_routes.router)
    app.include_router(ticket_routes.router)
    app.include_router(categories_routes.router)
    return app

app = create_app()
```

**Por que factory?**
- Testes podem chamar `create_app()` com configuração diferente
- CLI pode criar app sem a instância global
- Mais flexível

---

## Modelos ORM e Base de Dados

### O que é ORM?

**ORM** = Object-Relational Mapping. É uma técnica para converter entre dados relacionais (tabelas SQL) e objetos Python.

```
Banco de Dados (SQL)
    ↓
Converter ↔ (ORM)
    ↓
Código Python (Classes)
```

### Por que ORM separado de Domain Models?

**Domain Model** (`Ticket`, `Comment`)
- Puro, sem conhecimento de banco
- Foca em lógica de negócio
- Usa `@dataclass`
- Pode ter qualquer estrutura

**ORM Model** (`TicketORM`, `CommentORM`)
- Conhece de SQL e persistência
- Herda de SQLAlchemy `Base`
- Define colunas e tipos SQL
- Define relacionamentos

**Benefício:** Trocar banco de dados não afeta a lógica!

```python
# Domain (puro)
@dataclass
class Ticket:
    id: int
    title: str
    comments: list[Comment]

# ORM (específico do banco)
class TicketORM(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    comments = relationship("CommentORM")  # ← Específico do banco!
```

### `src/infrastructure/database.py` — Configuração SQLAlchemy

**O que é?**
Centraliza a configuração da base de dados.

```python
# Carregar variáveis de .env
DATABASE_URL = os.getenv("DATABASE_URL")

# Criar conexão com o banco
engine = create_engine(DATABASE_URL)

# Factory para criar sessões
SessionLocal = sessionmaker(bind=engine)

# Classe base para todos os models ORM
class Base(DeclarativeBase):
    pass
```

**Por que?**
- Um único lugar para configurar o banco
- Reutilizável em rotas, migrations, testes
- Fácil de alterar (mudar URL, adicionar logging, etc.)

---

### `src/infrastructure/models/ticket_orm.py` — Modelos ORM

**O que é?**
Define como os Tickets e Comments são armazenados no banco de dados.

```python
class TicketORM(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(String(5000), nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN)
    priority = Column(Enum(TicketPriority), default=TicketPriority.MEDIUM)
    category = Column(Enum(TicketCategory), default=TicketCategory.SOFTWARE)
    created_at = Column(DateTime, default=datetime.now)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relacionamento: um ticket tem muitos comentários
    comments = relationship(
        "CommentORM",
        back_populates="ticket",
        cascade="all, delete-orphan",  # Deleta comentários quando ticket é deletado
        lazy="joined"  # Carrega comentários automaticamente
    )
```

**Características importantes:**

| Recurso | O que faz | Exemplo |
|---------|-----------|---------|
| `Column` | Define uma coluna no banco | `Column(String(200))` |
| `primary_key=True` | Chave primária (ID único) | `id = Column(Integer, primary_key=True)` |
| `nullable=False` | Campo obrigatório | `title = Column(String(200), nullable=False)` |
| `default=` | Valor padrão | `status = Column(Enum(TicketStatus), default=TicketStatus.OPEN)` |
| `ForeignKey()` | Referencia outra tabela | `assigned_to = Column(Integer, ForeignKey("users.id"))` |
| `Enum` | Usa enums Python como tipo SQL | `status = Column(Enum(TicketStatus))` |
| `relationship()` | Relacionamento ORM | `comments = relationship("CommentORM")` |
| `cascade="all, delete-orphan"` | Deleta relacionados | Deletar ticket deleta comentários |
| `lazy="joined"` | Carrega dados relacionados | Carrega comentários com o ticket |

**Conversão Domain ↔ ORM:**

```python
# De ORM para Domain (quando vem do banco)
def orm_to_domain(ticket_orm: TicketORM) -> Ticket:
    return Ticket(
        id=ticket_orm.id,
        title=ticket_orm.title,
        description=ticket_orm.description,
        status=ticket_orm.status,
        priority=ticket_orm.priority,
        category=ticket_orm.category,
        created_at=ticket_orm.created_at,
        comments=[
            Comment(id=c.id, content=c.content)
            for c in ticket_orm.comments
        ]
    )

# De Domain para ORM (quando vai para o banco)
def domain_to_orm(ticket: Ticket) -> TicketORM:
    return TicketORM(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        priority=ticket.priority,
        category=ticket.category,
        created_at=ticket.created_at
    )
```

---

### `src/infrastructure/models/user_orm.py` — Modelo User

**O que é?**
Define o utilizador no banco de dados.

```python
class UserORM(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="USER")  # ADMIN, USER, SUPPORT
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    telephone = Column(String(20), nullable=True)  # Campo opcional
```

**Campos importantes:**
- `email` — único, não pode repetir
- `password_hash` — NUNCA armazenar a senha! Hash sempre
- `role` — define permissões (ADMIN, USER, SUPPORT)
- `is_active` — soft delete (marca como inativo em vez de apagar)
- `telephone` — opcional, pode ser NULL

---

## Alembic — Migrações de Banco de Dados

### O que é Alembic?

Alembic é uma ferramenta que **controla versões do schema do banco de dados**.

**Problema sem migrations:**
```python
# Versão 1 (Semana 2)
Base.metadata.create_all(engine)  # Cria tabelas

# Versão 2 (Semana 3)
# Como adicionar coluna "telephone" em users?
# Editar o model... e depois?
# O banco não sabe que mudou! Código fica fora de sync com banco.
```

**Solução com Alembic:**
```bash
# 1. Modificar o model ORM
# class UserORM:
#     telephone = Column(String(20))

# 2. Gerar migration automática
alembic revision --autogenerate -m "Add telephone to users"

# 3. Revisar a migration
# alembic/versions/xxx_add_telephone_to_users.py

# 4. Aplicar ao banco
alembic upgrade head

# ✅ Banco está sincronizado com código!
```

### Como funciona Alembic

```
migrations/
├── env.py                    ← Configuração do Alembic
├── script.py.mako           ← Template para novas migrations
├── alembic.ini              ← Arquivo de configuração
└── versions/
    ├── 1542ad98c7c7_create_initial_schema...py
    ├── 59b2b3227eb5_create_users_table.py
    ├── 05d6a98dc1c6_add_telephone_field_to_users.py
    └── 69b887a5d772_add_assigned_to_field_to_tickets.py
```

**Cada migration é um arquivo Python:**

```python
# migrations/versions/xxx_add_telephone_to_users.py

from alembic import op
import sqlalchemy as sa

def upgrade():
    """Aplicar a mudança (para frente)."""
    op.add_column('users', sa.Column('telephone', sa.String(20), nullable=True))

def downgrade():
    """Reverter a mudança (para trás)."""
    op.drop_column('users', 'telephone')
```

### `migrations/env.py` — Configuração

Este é o ficheiro mais importante do Alembic.

```python
# 1. Adicionar src ao path Python
sys.path.insert(0, str(Path(__file__).parent.parent))

# 2. Carregar .env
load_dotenv()

# 3. Importar a Base (OBRIGATÓRIO!)
from src.infrastructure.database import Base

# 4. Importar TODOS os models ORM
from src.infrastructure.models.ticket_orm import TicketORM, CommentORM
from src.infrastructure.models.user_orm import UserORM

# 5. Dizer ao Alembic que estes são os models
target_metadata = Base.metadata
```

**Por que importar todos os models?**
Se não importar, Alembic não saberá que existem e não as detectará em `--autogenerate`.

### Usar Alembic

**1. Gerar migration (automática):**
```bash
alembic revision --autogenerate -m "Add telephone to users"
```

Isto **compara** o banco com os models e cria a migration.

**2. Revisar a migration:**
```bash
cat migrations/versions/xxx_add_telephone_to_users.py
```

Verificar se está correto antes de aplicar.

**3. Aplicar ao banco:**
```bash
alembic upgrade head
```

Executa todas as migrations até à versão mais recente.

**4. Ver histórico:**
```bash
alembic history
```

Mostra todas as migrations aplicadas.

**5. Reverter última migration:**
```bash
alembic downgrade -1
```

**6. Ir para uma versão específica:**
```bash
alembic upgrade 1542ad98c7c7
```

### Migrations neste projeto

Este projeto tem 4 migrations:

1. **`1542ad98c7c7_create_initial_schema_with_tickets_and_comments.py`**
   - Cria tabelas `tickets` e `comments`
   - Define colunas básicas
   - Define relacionamentos

2. **`59b2b3227eb5_create_users_table.py`**
   - Cria tabela `users`
   - Define campos: id, name, email, password_hash, role, is_active, created_at

3. **`05d6a98dc1c6_add_telephone_field_to_users.py`**
   - Adiciona coluna `telephone` em users
   - Campo opcional (nullable=True)

4. **`69b887a5d772_add_assigned_to_field_to_tickets_with_foreign_key.py`**
   - Adiciona coluna `assigned_to` em tickets
   - Foreign key para users.id
   - Permite atribuir tickets a utilizadores

### Fluxo: Adicionar nova coluna

Vamos dizer que quer adicionar `priority_level` em users:

**Passo 1: Modificar o model ORM**
```python
# src/infrastructure/models/user_orm.py
class UserORM(Base):
    # ... colunas existentes ...
    priority_level = Column(Integer, default=5, nullable=False)  # ← NOVA
```

**Passo 2: Gerar migration**
```bash
alembic revision --autogenerate -m "Add priority_level to users"
```

Cria `migrations/versions/xxx_add_priority_level_to_users.py`

**Passo 3: Revisar**
```python
# migrations/versions/xxx_add_priority_level_to_users.py
def upgrade():
    op.add_column('users', sa.Column('priority_level', sa.Integer(), server_default='5', nullable=False))

def downgrade():
    op.drop_column('users', 'priority_level')
```

**Passo 4: Aplicar**
```bash
alembic upgrade head
```

✅ Banco sincronizado!

### Variáveis de ambiente

Alembic lê `DATABASE_URL` do `.env`:

```bash
# .env
DATABASE_URL=postgresql://user:password@localhost:5432/helpdesk_db
ENVIRONMENT=development
```

Depois no código:
```python
# migrations/env.py
url = os.getenv("DATABASE_URL", "sqlite:///./test.db")
```

---

## Princípios SOLID Aplicados

SOLID é um acrónimo para 5 princípios de design. Vamos ver como estão aplicados:

### 1. SRP — Single Responsibility Principle

**"Uma classe deve ter uma única razão para mudar."**

```
Ticket (Domain)         → Responsabilidade: representar um ticket
TicketService           → Responsabilidade: lógica de negócio
InMemoryRepository      → Responsabilidade: guardar em memória
TicketResponse          → Responsabilidade: formato HTTP
ticket_routes.py        → Responsabilidade: mapear HTTP para service
```

**Exemplo:** Se mudar como guardamos dados (memória → banco):
- Muda: `InMemoryTicketRepository`
- Não muda: `TicketService`, `TicketResponse`, routes
- ✅ Responsabilidades separadas

---

### 2. OCP — Open/Closed Principle

**"Aberto para extensão, fechado para modificação."**

Quero adicionar novo tipo de repositório (SQLAlchemy):

```python
class SQLAlchemyTicketRepository(ITicketRepository):  # ← Nova implementação
    def create(self, ticket):
        # Guardar em PostgreSQL
        pass
```

**Mudanças:**
- Cria novo ficheiro (extensão)
- Muda uma linha em `ticket_routes.py` (nova implementação)
- Não mexes em `TicketService` ou `TicketResponse`

✅ Aberto para extensão, fechado para modificação

---

### 3. LSP — Liskov Substitution Principle

**"Subclasses devem ser substituíveis pelas superclasses."**

```python
# Isto funciona com InMemoryRepository:
service = TicketService(InMemoryTicketRepository())
ticket = service.create_ticket(...)

# Isto funcionará com SQLAlchemyRepository (sem mudar service):
service = TicketService(SQLAlchemyTicketRepository(session))
ticket = service.create_ticket(...)  # Mesmo código!
```

Qualquer implementação de `ITicketRepository` funciona.

✅ Substituição sem quebrar

---

### 4. ISP — Interface Segregation Principle

**"Clientes não devem depender de interfaces que não usam."**

```python
# ❌ Errado: interface gigante
class IRepository:
    def create(self): ...
    def read(self): ...
    def update(self): ...
    def delete(self): ...
    def search(self): ...
    def export_to_csv(self): ...
    def print_report(self): ...
```

```python
# ✅ Correto: interfaces focadas
class ITicketRepository:
    def create(self, ticket): ...
    def get_all(self, ...): ...
    def get_by_id(self, id): ...
    def update(self, ticket): ...
    def add_comment(self, comment): ...
```

Cada interface é focada no que é necessário.

✅ Dependências claras

---

### 5. DIP — Dependency Inversion Principle

**"Depende de abstrações, não de concretos."**

```python
# ❌ Errado: acoplado a implementação específica
class TicketService:
    def __init__(self):
        self._repo = InMemoryTicketRepository()  # Acoplado!

# ✅ Correto: depende de interface
class TicketService:
    def __init__(self, repository: ITicketRepository):  # Interface!
        self._repo = repository

# Uso:
service = TicketService(InMemoryTicketRepository())  # Injetar
service = TicketService(SQLAlchemyTicketRepository())  # Outra injeção
```

Service não sabe qual implementação está a usar. Podes trocar sem mexer nele.

✅ Desacoplado

---

## DRY — Don't Repeat Yourself

**"Não repitas código. Reutiliza."**

### Exemplo 1: PaginatedResponse genérico

❌ Sem DRY (duplicação):
```python
class PaginatedTicketResponse:
    items: list[TicketResponse]
    total: int
    page: int
    size: int
    pages: int

class PaginatedCommentResponse:
    items: list[CommentResponse]
    total: int
    page: int
    size: int
    pages: int

# Mesmo padrão repetido!
```

✅ Com DRY (genérico):
```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]          # T = TicketResponse, CommentResponse, etc
    total: int
    page: int
    size: int
    pages: int

# Uso:
PaginatedResponse[TicketResponse]
PaginatedResponse[CommentResponse]
PaginatedResponse[UserResponse]  # Funciona com qualquer tipo!
```

**Benefício:** Uma classe serve para infinitos tipos.

---

### Exemplo 2: Guard Clauses centralizados

❌ Sem DRY (validação repetida):
```python
def create_ticket(request):
    if not request.title: raise ValueError(...)
    if not request.description: raise ValueError(...)
    return service.create_ticket(...)

def update_ticket(request):
    if not request.status: raise ValueError(...)
    return service.update_ticket(...)

# Validação repetida!
```

✅ Com DRY (validação no schema):
```python
class CreateTicketRequest(BaseModel):
    title: str = Field(..., min_length=1)      # Pydantic valida
    description: str = Field(..., min_length=1)

# Routes não precisa de validar — Pydantic faz
@router.post("/")
def create_ticket(request: CreateTicketRequest):
    return service.create_ticket(...)  # Já é válido
```

**Benefício:** Validação num único lugar (Pydantic schemas).

---

## Guard Clauses

**"Validações no início da função. Rejeita cedo. Retorna ou lança."**

### Exemplo 1: Antes (sem guard clauses)

```python
def get_ticket(ticket_id):
    ticket = self._repo.get_by_id(ticket_id)
    if ticket:
        # ... 50 linhas de lógica ...
        if ticket.is_valid():
            # ... mais 30 linhas ...
            return ticket
    else:
        raise TicketNotFoundError()
```

**Problemas:**
- Lógica aninhada (if dentro de if)
- Difícil de seguir
- Erro pode estar profundamente aninhado

### Exemplo 2: Depois (com guard clauses)

```python
def get_ticket(ticket_id):
    # Guard Clause: rejeitar cedo
    ticket = self._repo.get_by_id(ticket_id)
    if not ticket:
        raise TicketNotFoundError(ticket_id)

    # Aqui, sabemos que ticket existe
    # Lógica é reta, sem aninhamento
    # ... 80 linhas de lógica clara ...
    return ticket
```

**Benefícios:**
- Código mais legível
- Lógica principal clara
- Erros são óbvios

### Guard Clauses no projeto

```python
# Em InMemoryTicketRepository.create()
if not ticket:
    raise ValueError("Ticket cannot be None")

# Em TicketService.get_ticket()
if not ticket:
    raise TicketNotFoundError(ticket_id)

# Em TicketService.add_comment()
if not content or not content.strip():
    raise ValueError("Comment content cannot be empty")
```

**Padrão:**
1. Validar input no início
2. Se inválido: lança exceção ou retorna cedo
3. Resto da função assume dados válidos

---

## Padrão Repository

**"Abstrai como os dados são guardados."**

### Por que existe este padrão?

Imagina que o teu código depende diretamente da implementação:

```python
class TicketService:
    def __init__(self):
        self._db = SQLAlchemy()  # Acoplado!
        self._cache = Redis()     # Acoplado!
        self._api = ExternalAPI() # Acoplado!

    def get_ticket(self, id):
        # Precisa saber de 3 implementações diferentes
        # Testável? Não! Depende de externos
        # Reutilizável? Não! Tem dependências específicas
```

### Com padrão Repository

```python
class TicketService:
    def __init__(self, repository: ITicketRepository):
        self._repo = repository  # Abstração

    def get_ticket(self, id):
        # Não sabe como funciona, só usa o contrato
        return self._repo.get_by_id(id)

# Uso:
service = TicketService(InMemoryRepository())       # Memória
service = TicketService(SQLAlchemyRepository())     # PostgreSQL
service = TicketService(MockRepository())          # Testes
```

### Arquitetura do padrão

```
Domain Layer
    ↑
    │ (depends on interface)
    │
┌───┴────────────────────────┐
│   ITicketRepository         │  ← Interface (contrato)
│   - create()                │
│   - get_all()               │
│   - get_by_id()             │
│   - update()                │
│   - add_comment()           │
└──────────────────────────────┘

Infrastructure Layer
    ↓
┌──────────────────────────────┐
│ InMemoryTicketRepository     │  ← Implementação 1
└──────────────────────────────┘

┌──────────────────────────────┐
│ SQLAlchemyTicketRepository   │  ← Implementação 2 (Semana 4)
└──────────────────────────────┘

┌──────────────────────────────┐
│ MockTicketRepository         │  ← Implementação 3 (Testes)
└──────────────────────────────┘
```

### Fluxo na Semana 2 vs Semana 4

**Semana 2:**
```
POST /tickets
     ↓
ticket_routes.py chama service
     ↓
service chama InMemoryTicketRepository.create()
     ↓
Guarda em `_tickets = {}`
     ↓
Retorna ticket
```

**Semana 4:**
```
POST /tickets
     ↓
ticket_routes.py chama service  ← SEM MUDANÇA!
     ↓
service chama SQLAlchemyTicketRepository.create()  ← MUDOU AQUI
     ↓
Guarda em PostgreSQL
     ↓
Retorna ticket
```

**Mudanças:**
- 1 linha em `ticket_routes.py`
- Criar novo ficheiro `sqlalchemy_ticket_repository.py`
- Criar ficheiros de ORM e configuração

**Não muda:**
- Service
- Routes (lógica)
- API contracts

---

## Fluxo de Uma Requisição

Vamos acompanhar uma requisição do início ao fim.

### Exemplo: POST /tickets

```
1. Cliente envia
   POST /tickets
   {
     "title": "Login broken",
     "description": "Cannot access",
     "priority": "high",
     "category": "access"
   }

2. FastAPI recebe e valida com Pydantic
   CreateTicketRequest(
     title="Login broken",
     description="Cannot access",
     priority=TicketPriority.HIGH,
     category=TicketCategory.ACCESS
   )

3. Chama a função create_ticket()
   → request está validado
   → service pode confiar nos dados

4. ticket_routes.py:create_ticket(request)
   → service.create_ticket(
       title=request.title,
       description=request.description,
       priority=request.priority,
       category=request.category
     )

5. ticket_service.py:create_ticket()
   → Validações de negócio:
     if not title.strip(): raise ValueError()
   → Cria modelo de domínio:
     ticket = Ticket(id=0, title=..., ...)
   → Chama repositório:
     return self._repository.create(ticket)

6. in_memory_ticket_repository.py:create()
   → Atribui ID:
     ticket.id = self._next_id
   → Guarda em memória:
     self._tickets[ticket.id] = ticket
   → Retorna:
     return ticket

7. Volta para service
   → Retorna o ticket com ID atribuído

8. Volta para routes
   → Converte para TicketResponse (Pydantic)

9. FastAPI converte para JSON e retorna
   HTTP 201 Created
   {
     "id": 1,
     "title": "Login broken",
     "description": "Cannot access",
     "status": "open",
     "priority": "high",
     "category": "access",
     "created_at": "2024-01-15T10:30:00"
   }

10. Cliente recebe a resposta
```

### Fluxo de camadas visualizado

```
[HTTP JSON]
    ↓
[Pydantic Validation] ← Rejeita dados inválidos
    ↓
[Routes] ← Chama service
    ↓
[Service] ← Lógica de negócio, levanta exceções
    ↓
[Repository] ← Guarda dados
    ↓
[Volta pela cadeia] ← Cada camada trata o seu
    ↓
[JSON Response]
```

---

## Como Evoluir o Projeto

Depois de compreenderes o projeto atual, podes evoluir em várias direções.

### Passo 1: Semana 3 — Completar sem mudança arquitetónica

Já está implementado! A arquitetura suporta:
- ✅ Filtros (status, priority, category)
- ✅ Paginação (page, size)
- ✅ Comentários (POST /tickets/{id}/comments)

Não precisa de mudança arquitetónica.

### Passo 2: Semana 4 — PostgreSQL com Alembic ✅ (Já Implementado!)

**Status:** ✅ Já está feito! Este projeto tem:

✅ **Alembic configurado** — `alembic.ini` + `migrations/`
✅ **Modelos ORM** — `ticket_orm.py`, `comment_orm.py`, `user_orm.py`
✅ **Base de dados** — `src/infrastructure/database.py` com SQLAlchemy
✅ **Migrations** — 4 migrations já criadas:
   - Criar tabelas iniciais (tickets, comments)
   - Criar tabela users
   - Adicionar coluna telephone em users
   - Adicionar coluna assigned_to em tickets

**Como usar o PostgreSQL:**

1. **Instalar PostgreSQL:**
   ```bash
   # macOS
   brew install postgresql@15
   
   # Linux
   sudo apt install postgresql
   
   # Windows
   # Descarregar de https://www.postgresql.org/download/windows/
   ```

2. **Criar database:**
   ```bash
   createdb helpdesk_db
   ```

3. **Configurar variáveis de ambiente:**
   ```bash
   # .env
   DATABASE_URL=postgresql://localhost:5432/helpdesk_db
   ENVIRONMENT=development
   ```

4. **Aplicar migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Trocar para SQLAlchemy repository:**
   ```python
   # src/api/routes/ticket_routes.py
   from src.infrastructure.database import SessionLocal
   from src.infrastructure.repositories.sqlalchemy_ticket_repository import SQLAlchemyTicketRepository
   
   _repository = SQLAlchemyTicketRepository(SessionLocal())
   ```

**Como adicionar nova coluna:**

1. Editar o model ORM:
   ```python
   # src/infrastructure/models/ticket_orm.py
   class TicketORM(Base):
       # ... campos existentes ...
       new_field = Column(String(100), nullable=True)  # ← NOVA COLUNA
   ```

2. Gerar migration:
   ```bash
   alembic revision --autogenerate -m "Add new_field to tickets"
   ```

3. Revisar `migrations/versions/xxx_add_new_field_to_tickets.py`

4. Aplicar:
   ```bash
   alembic upgrade head
   ```

### Passo 3: Autenticação — Saber quem fez o quê

**O que adicionar:**
1. Tabela `users` com username/password
2. Campo `user_id` nos tickets e comments
3. Middleware JWT para autenticar requisições
4. Routes de login/logout

**Exemplo:**
```python
@router.post("/login")
def login(credentials: LoginRequest) -> TokenResponse:
    """Autentica e retorna token JWT."""
    user = service.authenticate(credentials.username, credentials.password)
    token = create_jwt_token(user.id)
    return TokenResponse(access_token=token)

@router.post("/tickets")
def create_ticket(request: CreateTicketRequest, current_user: User = Depends(get_current_user)):
    """Criar ticket — requer autenticação."""
    ticket = service.create_ticket(
        title=request.title,
        description=request.description,
        user_id=current_user.id,  # Associar ao utilizador
        ...
    )
    return ticket
```

### Passo 4: Testes — Garantir que funciona

**Testes unitários:**
```python
def test_create_ticket():
    repo = MockTicketRepository()
    service = TicketService(repo)

    ticket = service.create_ticket("Title", "Description")

    assert ticket.id == 1
    assert ticket.title == "Title"
    assert ticket.status == TicketStatus.OPEN
```

**Testes de integração:**
```python
def test_create_ticket_via_api():
    response = client.post("/tickets", json={
        "title": "Test",
        "description": "Test description"
    })

    assert response.status_code == 201
    assert response.json()["title"] == "Test"
```

**Testes E2E:**
```python
def test_full_workflow():
    # 1. Criar ticket
    response = client.post("/tickets", json=...)
    ticket_id = response.json()["id"]

    # 2. Adicionar comentário
    response = client.post(f"/tickets/{ticket_id}/comments", json=...)
    assert response.status_code == 201

    # 3. Atualizar status
    response = client.patch(f"/tickets/{ticket_id}", json={"status": "in_progress"})
    assert response.json()["status"] == "in_progress"
```

### Passo 5: Deployment — Colocar em produção

**Docker:**
```dockerfile
FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Variáveis de ambiente:**
```bash
DATABASE_URL=postgresql://user:pass@postgres:5432/helpdesk
ENVIRONMENT=production
LOG_LEVEL=info
```

**CI/CD:**
```yaml
# GitHub Actions
name: Deploy
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: pip install pytest
      - run: pytest
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - run: docker build -t helpdesk:latest .
      - run: docker push registry/helpdesk:latest
```

### Passo 6: Funcionalidades adicionais

**Possibilidades infinitas:**

1. **Notificações**
   - Email quando ticket é criado
   - SMS para atualizações urgentes

2. **Relatórios**
   - Tickets por categoria
   - Tempo médio de resolução
   - Utilizador mais ativo

3. **Automação**
   - Fechar tickets sem resposta há 30 dias
   - Escalar para gestor se prioridade urgente

4. **Integração externa**
   - Slack notifications
   - Sincronizar com Google Calendar
   - Webhook para sistemas externos

5. **Analytics**
   - Dashboard de métricas
   - Gráficos de tendências
   - Previsões de volume

---

## Checklist de Aprendizagem

Depois de ler este documento, consegues responder a isto?

### Arquitetura
- [ ] Que é uma arquitetura em camadas?
- [ ] Por que Domain está separado de Infrastructure?
- [ ] Como flui uma requisição através das camadas?

### Padrões
- [ ] O que é o padrão Repository? Por que é útil?
- [ ] Como a interface `ITicketRepository` permite trocar implementações?
- [ ] O que é injeção de dependência?

### SOLID
- [ ] Qual é o princípio SRP? Onde está aplicado?
- [ ] O que é DIP? Como o service usa DIP?
- [ ] Como podes adicionar nova implementação sem quebrar o código?

### Implementação
- [ ] Qual a diferença entre `Ticket` (domain) e `TicketResponse` (API)?
- [ ] Por que levantamos `TicketNotFoundError` no service e não `HTTPException`?
- [ ] Como funciona o `PaginatedResponse[T]` genérico?

### Evolução
- [ ] Como trocar de memória para PostgreSQL?
- [ ] Quantas linhas de código mudas em `TicketService`?
- [ ] Como adicionar autenticação?

---

## Conclusão

Parabéns! Leste todo o documento.

Este projeto mostra como construir APIs profissionais:
- ✅ Arquitetura em camadas
- ✅ Separação de conceitos
- ✅ Fácil de testar
- ✅ Fácil de manter
- ✅ Fácil de evoluir

**Próximos passos:**
1. Entender cada ficheiro (relê o código com comentários)
2. Fazer mudanças pequenas (adicionar campo a Ticket)
3. Implementar Semana 4 (trocar para PostgreSQL)
4. Escrever testes

**Recursos:**
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- [FastAPI Docs](https://fastapi.tiangolo.com/)

Bom código! 🚀
