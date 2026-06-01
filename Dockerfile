# syntax=docker/dockerfile:1.7

# ============================================================================
# Stage 1: Builder - instala dependências com uv
# ============================================================================
FROM python:3.12-slim AS builder

# Instalar uv (gestor de dependências do projeto)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Variáveis de ambiente para build
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências do sistema necessárias para compilar pacotes (psycopg2, bcrypt, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar manifests primeiro para aproveitar cache de layer
COPY pyproject.toml uv.lock ./

# Instalar dependências (sem o próprio projeto, para melhor cache)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copiar o resto do código
COPY . .

# Instalar o projeto
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# ============================================================================
# Stage 2: Runtime - imagem final mínima
# ============================================================================
FROM python:3.12-slim AS runtime

# Dependências de runtime (libpq para psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Criar utilizador não-root por segurança
RUN groupadd --system app && useradd --system --gid app --home /app app

WORKDIR /app

# Copiar venv e código do stage builder
COPY --from=builder --chown=app:app /app /app

# Colocar binários do venv no PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

USER app

EXPOSE 8000

# Health check usa o endpoint /health da app
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT:-8000}/health" || exit 1

# Iniciar a aplicação:
# 1. Aplicar migrações Alembic (idempotente — só corre o que falta)
# 2. Subir uvicorn na porta indicada por $PORT (Render injeta) ou 8000 (local)
CMD ["sh", "-c", "alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
