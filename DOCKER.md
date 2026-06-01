# 🐳 Docker - HelpDesk Hub API

Guia para executar a aplicação com Docker e Docker Compose.

## 📦 Arquivos

| Arquivo | Propósito |
|---------|-----------|
| `Dockerfile` | Build multi-stage da imagem da API (Python 3.12 + uv) |
| `docker-compose.yml` | Orquestração da API + PostgreSQL |
| `.dockerignore` | Ficheiros excluídos do contexto de build |

## 🚀 Início Rápido

### 1. Preparar variáveis de ambiente

```bash
# Copiar template
cp .env.example .env

# Editar .env e garantir que SECRET_KEY tem pelo menos 32 caracteres
# Gerar uma nova: openssl rand -hex 32
```

> ⚠️ Variáveis críticas no `.env`:
> - `SECRET_KEY` (obrigatório, mínimo 32 chars)
> - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
> - `DATABASE_URL` (usado pela app quando corre fora do compose)

### 2. Subir os containers

```bash
# Build + start (em foreground)
docker compose up --build

# Em background
docker compose up -d --build
```

### 3. Aceder à API

- API: http://localhost:8000
- Docs (Swagger): http://localhost:8000/docs
- Health: http://localhost:8000/health
- PostgreSQL: `localhost:5432`

## 🛠️ Comandos Úteis

```bash
# Ver logs em tempo real
docker compose logs -f api
docker compose logs -f postgres

# Parar tudo (mantém volumes)
docker compose down

# Parar e remover volumes (apaga BD!)
docker compose down -v

# Rebuild apenas a API
docker compose build api
docker compose up -d api

# Executar comando dentro do container da API
docker compose exec api bash
docker compose exec api alembic current
docker compose exec api alembic upgrade head

# Aceder ao psql
docker compose exec postgres psql -U helpdesk_user -d helpdesk_db
```

## 🏗️ Estrutura do Dockerfile

O Dockerfile usa **multi-stage build** para imagens menores:

1. **Builder stage**: instala `uv`, compila dependências (psycopg2, bcrypt)
2. **Runtime stage**: imagem mínima Python 3.12-slim, apenas com runtime libs

Características:
- Usa `uv sync --frozen --no-dev` para reprodutibilidade
- Utilizador não-root (`app`) por segurança
- Healthcheck integrado via `/health`
- Cache de layers otimizado (manifests antes do código)

## 🔄 Migrações Alembic

O serviço `api` executa `alembic upgrade head` automaticamente antes de iniciar a aplicação. Para criar uma nova migração:

```bash
docker compose exec api alembic revision --autogenerate -m "descrição"
docker compose exec api alembic upgrade head
```

## 🧪 Executar Testes no Container

```bash
# Adicionar deps de teste (se ainda não estão no lock)
docker compose exec api uv add --dev pytest pytest-asyncio httpx

# Rodar testes
docker compose exec api uv run pytest
```

## 🐛 Troubleshooting

**API não inicia — erro de SECRET_KEY**
```
❌ ERRO: SECRET_KEY não configurada no .env
```
→ Gerar uma e adicionar ao `.env`: `openssl rand -hex 32`

**API não conecta ao Postgres**
→ Verifique que `DATABASE_URL` no compose usa `postgres` (nome do serviço), não `localhost`.

**Porta 5432 ou 8000 já em uso**
→ Mude o mapeamento no `docker-compose.yml`:
```yaml
ports:
  - "5433:5432"  # host:container
```

**Quero apagar tudo e começar do zero**
```bash
docker compose down -v
docker compose up --build
```
