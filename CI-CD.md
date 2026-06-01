# 🚀 CI/CD — HelpDesk Hub API

Guia completo do pipeline de Continuous Integration e Continuous Deployment desta aplicação. Cobre **setup do zero** no Render e GitHub Actions, com baby steps detalhados.

> Versão final do pipeline. Se for o teu primeiro contacto com CI/CD, segue de cima a baixo.

---

## 📑 Índice

1. [Visão Geral](#1-visão-geral)
2. [Pré-requisitos](#2-pré-requisitos)
3. [Parte A — Configurar o Render](#3-parte-a--configurar-o-render)
4. [Parte B — Configurar o GitHub](#4-parte-b--configurar-o-github)
5. [Parte C — O Workflow do GitHub Actions](#5-parte-c--o-workflow-do-github-actions)
6. [Parte D — Ajustes no Dockerfile](#6-parte-d--ajustes-no-dockerfile)
7. [Como Testar o Pipeline](#7-como-testar-o-pipeline)
8. [Fluxo Diário de Trabalho](#8-fluxo-diário-de-trabalho)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Visão Geral

### Stack

| Componente | Tecnologia |
|------------|------------|
| Linguagem | Python 3.11 |
| Framework | FastAPI |
| Base de dados | PostgreSQL 16 |
| Gestor de dependências | uv |
| Containerização | Docker (multi-stage) |
| Migrações | Alembic |
| CI | GitHub Actions |
| CD / Hosting | Render.com |

### Fluxo

```
┌─────────────┐                     ┌─────────────────┐
│  Developer  │                     │     GitHub      │
└──────┬──────┘                     └────────┬────────┘
       │                                     │
       │  git push main                      │
       └────────────────────────────────────►│
                                             │
                                             ▼
                                ┌────────────────────────┐
                                │   GH Actions: CI       │
                                │   (job: test)          │
                                │                        │
                                │  • Postgres 16 service │
                                │  • uv sync             │
                                │  • uv run pytest       │
                                └────────┬───────────────┘
                                         │ ✅ tests pass
                                         ▼
                                ┌────────────────────────┐
                                │   GH Actions: CD       │
                                │   (job: deploy)        │
                                │                        │
                                │  • curl deploy hook    │
                                │  • poll Render API     │
                                │  • wait for 'live'     │
                                └────────┬───────────────┘
                                         │ webhook
                                         ▼
                                ┌────────────────────────┐
                                │       Render           │
                                │                        │
                                │  • build Docker image  │
                                │  • alembic upgrade head│
                                │  • uvicorn start       │
                                └────────┬───────────────┘
                                         │
                              ┌──────────┴──────────┐
                              ▼                     ▼
                       ┌──────────────┐    ┌──────────────┐
                       │ Web Service  │◄──►│  PostgreSQL  │
                       │ (FastAPI)    │    │  (managed)   │
                       └──────────────┘    └──────────────┘
```

### Princípios

- **Testes antes de deploy** — nenhum deploy acontece se os testes falharem
- **Deploy controlado pelo GitHub Actions** — Render fica em modo manual; o workflow é o único a disparar deploys
- **Migrações automáticas** — `alembic upgrade head` corre antes do `uvicorn` em cada deploy
- **Branch protegido** — `main` só recebe merges com CI verde
- **Sem segredos no código** — tudo vive em GitHub Secrets ou Render environment variables

---

## 2. Pré-requisitos

Antes de começares, garante que tens:

- ✅ Conta no [GitHub](https://github.com) com o repositório `demo-help-desk-hub-api`
- ✅ Dockerfile do projeto a funcionar localmente (testa com `docker compose up`)
- ✅ Testes a passar localmente (`uv run pytest`)
- ✅ Acesso a um terminal com `openssl` (para gerar secrets) ou usa <https://www.random.org/strings/>

---

## 3. Parte A — Configurar o Render

### A.1 Criar a conta

1. Vai a <https://render.com>
2. Clica em **Get Started** ou **Sign In**
3. Escolhe **Sign in with GitHub**
4. Na janela do GitHub que abre, clica **Authorize Render**
5. (Pode pedir password e 2FA)

### A.2 Instalar a GitHub App do Render

Esta é a parte que dá ao Render permissão para **ler o teu repositório**.

1. No Render Dashboard, clica em **New +** → **Web Service**
2. Vais ver "Connect a repository" → **Configure account** (botão azul)
3. Abre uma página do GitHub:
   ```
   Where do you want to install Render?
     ● @teu-username (Personal)
   
   Repository access:
     ○ All repositories
     ● Only select repositories  ← recomendado por segurança
       └─ ☑ demo-help-desk-hub-api
   ```
4. Escolhe **Only select repositories** e seleciona o repo
5. Clica **Install**
6. Voltas automaticamente para o Render

> 💡 Mais tarde podes mudar isto em GitHub → Settings → Applications → Installed GitHub Apps → Render → Configure.

### A.3 Criar o PostgreSQL

1. No Render Dashboard → **New +** → **PostgreSQL**
2. Preenche:

   | Campo | Valor |
   |-------|-------|
   | **Name** | `helpdesk-db` |
   | **Database** | `helpdesk` (auto-gerado) |
   | **User** | `helpdesk_user` (auto-gerado) |
   | **Region** | **Frankfurt** (mais perto de PT) |
   | **PostgreSQL Version** | **16** |
   | **Plan** | Free |

3. Clica em **Create Database**
4. Espera ~1-2 minutos até o status passar para **Available**
5. Na página do serviço, copia a **Internal Database URL**:
   - Formato: `postgresql://user:password@dpg-xxx.frankfurt-postgres.render.com/dbname`
   - **Internal**, não External — é mais rápido e seguro (rede privada do Render)
6. Guarda este URL — vais precisar no próximo passo

### A.4 Criar o Web Service

1. No Dashboard → **New +** → **Web Service**
2. Seleciona o repositório `demo-help-desk-hub-api` da lista
3. Preenche:

   | Campo | Valor |
   |-------|-------|
   | **Name** | `helpdesk-api` |
   | **Region** | **Frankfurt** (igual à BD!) |
   | **Branch** | `main` |
   | **Root Directory** | (em branco) |
   | **Runtime** | **Docker** |
   | **Plan** | Free |

4. **🔑 Auto-Deploy** → muda para **No** (ESTE é o passo chave para CI/CD via GitHub Actions)
5. Clica em **Advanced** para abrir as Environment Variables

### A.5 Configurar Environment Variables

Adiciona uma a uma em **Environment Variables**:

| Key | Value | Notas |
|-----|-------|-------|
| `DATABASE_URL` | (cola a Internal Database URL do passo A.3) | |
| `SECRET_KEY` | (gera com `openssl rand -hex 32`) | mínimo 32 chars |
| `ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | |
| `ENVIRONMENT` | `production` | |
| `LOG_LEVEL` | `info` | |
| `ALLOWED_ORIGINS` | `https://app.exemplo.com` | ajusta ao teu frontend |
| `PORT` | `8000` | o Render injeta este, mas explicita por segurança |

> 💡 Para gerar o SECRET_KEY:
> ```bash
> # Linux/Mac
> openssl rand -hex 32
> 
> # Windows PowerShell
> [System.BitConverter]::ToString((1..32 | ForEach-Object { Get-Random -Maximum 256 })).Replace("-","").ToLower()
> ```

6. Clica **Create Web Service**
7. O Render vai começar um primeiro build automaticamente — **isto é normal e pode falhar** porque ainda não temos o workflow configurado. Não te preocupes.

### A.6 Obter o Deploy Hook

1. No serviço **helpdesk-api** → **Settings** (barra lateral)
2. Procura a secção **Deploy Hook**
3. Copia o URL — formato:
   ```
   https://api.render.com/deploy/srv-XXXXXX?key=YYYYYY
   ```
4. ⚠️ **Trata isto como password** — quem tiver este URL pode disparar deploys

### A.7 Criar uma API Key do Render

Esta é usada para o workflow **acompanhar** o estado do deploy (não apenas dispará-lo).

1. Canto superior direito → clica no teu avatar → **Account Settings**
2. Barra lateral → **API Keys**
3. Clica **Create API Key**
4. Nome: `github-actions-cicd`
5. Copia a key (formato `rnd_XXXXXXXXXXXXXXXXXXXXXXXXXXXX`)
6. ⚠️ Esta é mostrada **uma única vez** — guarda já

### A.8 Anotar o Service ID

1. Volta ao Web Service no Dashboard
2. Olha para o URL no browser:
   ```
   https://dashboard.render.com/web/srv-XXXXXXXXXXXXXXX
                                       └─────┬─────┘
                                    este é o SERVICE_ID
   ```
3. Copia tudo a partir de `srv-` (ex: `srv-d8erj042m8qs7398r8mg`)

✅ **Render está pronto.** Tens três valores guardados:

```
RENDER_DEPLOY_HOOK = https://api.render.com/deploy/srv-XXX?key=YYY
RENDER_API_KEY     = rnd_XXXXXXXXXXXXXXXXXXXXXXXXXXXX
RENDER_SERVICE_ID  = srv-XXXXXXXXXXXXXXX
```

---

## 4. Parte B — Configurar o GitHub

### B.1 Adicionar Secrets

1. Vai ao repositório no GitHub
2. **Settings** (na barra superior do repo) → **Secrets and variables** → **Actions**
3. Clica **New repository secret** para cada um:

   | Name | Value |
   |------|-------|
   | `RENDER_DEPLOY_HOOK` | (do passo A.6) |
   | `RENDER_API_KEY` | (do passo A.7) |
   | `RENDER_SERVICE_ID` | (do passo A.8) |

4. Após adicionar, vais ver os 3 secrets listados (valores ocultos)

### B.2 (Recomendado) Proteger o branch `main`

Garante que ninguém consegue fazer merge para `main` sem testes a passar.

1. **Settings** → **Branches** → **Add branch protection rule**
2. **Branch name pattern**: `main`
3. Marca:
   - ✅ **Require a pull request before merging**
   - ✅ **Require status checks to pass before merging**
     - Search: escreve `Run Tests` e seleciona (aparece depois do primeiro workflow correr)
   - ✅ **Require branches to be up to date before merging**
4. Clica **Create**

✅ **GitHub está pronto.**

---

## 5. Parte C — O Workflow do GitHub Actions

### C.1 Estrutura do ficheiro

O workflow vive em [.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml). Tem dois jobs:

| Job | Quando corre | Faz |
|-----|--------------|-----|
| `test` | PRs e pushes para `main` | Testes com pytest contra Postgres |
| `deploy` | **Apenas** push para `main` E depois de `test` passar | Dispara deploy no Render e espera |

### C.2 Anatomia completa

```yaml
name: CI/CD

on:
  push:
    branches: [main]      # CD: deploy quando merge em main
  pull_request:
    branches: [main]      # CI: testes em PRs

jobs:
  # ========================================
  # CI - Run tests
  # ========================================
  test:
    name: Run Tests
    runs-on: ubuntu-latest

    services:
      postgres:                          # Container Postgres para os testes
        image: postgres:16
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up uv
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true             # cacheia downloads do uv

      - name: Install dependencies
        run: uv sync --all-extras --dev

      - name: Run pytest
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test_db
          SECRET_KEY: test_secret_key_at_least_32_characters_long_for_ci
          ALGORITHM: HS256
          ACCESS_TOKEN_EXPIRE_MINUTES: "30"
          ENVIRONMENT: development
          ALLOWED_ORIGINS: http://localhost:3000
        run: uv run pytest

  # ========================================
  # CD - Deploy to Render
  # ========================================
  deploy:
    name: Deploy to Render
    needs: test                          # bloqueia se test falhar
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest

    steps:
      - name: Trigger Render deploy and wait for completion
        env:
          RENDER_DEPLOY_HOOK: ${{ secrets.RENDER_DEPLOY_HOOK }}
          RENDER_API_KEY: ${{ secrets.RENDER_API_KEY }}
          RENDER_SERVICE_ID: ${{ secrets.RENDER_SERVICE_ID }}
        run: |
          set -euo pipefail

          echo "🚀 Triggering Render deploy..."
          RESPONSE=$(curl -fsSL -X POST "$RENDER_DEPLOY_HOOK")
          echo "Response: $RESPONSE"

          DEPLOY_ID=$(echo "$RESPONSE" | jq -r '.deploy.id // empty')
          if [ -z "$DEPLOY_ID" ]; then
            echo "⚠️ Could not extract deploy id"
            exit 0
          fi

          echo "📦 Deploy ID: $DEPLOY_ID"
          echo "⏳ Polling deploy status (max ~10 min)..."

          for i in $(seq 1 40); do
            STATUS=$(curl -fsSL \
              -H "Authorization: Bearer $RENDER_API_KEY" \
              "https://api.render.com/v1/services/$RENDER_SERVICE_ID/deploys/$DEPLOY_ID" \
              | jq -r '.status')

            echo "[$i/40] Status: $STATUS"

            case "$STATUS" in
              live)
                echo "✅ Deploy succeeded!"
                exit 0
                ;;
              build_failed|update_failed|canceled|deactivated)
                echo "❌ Deploy failed with status: $STATUS"
                exit 1
                ;;
              created|build_in_progress|update_in_progress|pre_deploy_in_progress)
                sleep 15
                ;;
              *)
                echo "⚠️ Unknown status: $STATUS"
                sleep 15
                ;;
            esac
          done

          echo "❌ Timeout"
          exit 1
```

### C.3 Decisões importantes explicadas

**`services.postgres`**
Postgres num container ao lado do runner. Os testes apontam para `localhost:5432`. Mais leve e rápido que instalar Postgres manualmente.

**`needs: test`**
O job `deploy` só corre se `test` reportar sucesso. Se algum teste falhar, **nada vai para produção**.

**`if: github.event_name == 'push' && github.ref == 'refs/heads/main'`**
Filtra o gatilho: corre apenas em push direto para `main`. Em PRs, `test` corre mas `deploy` é skipped.

**Polling do estado do deploy**
O webhook do Render retorna `200 OK` imediatamente, mas o build pode demorar 5-10 min. O loop interroga a Render API a cada 15s para saber se o deploy ficou `live`, falhou, ou continua em curso. Sem isto, o GitHub Actions diria "success" antes do deploy realmente terminar.

**Estados terminais tratados**

| Status | Resultado |
|--------|-----------|
| `live` | ✅ Workflow passa |
| `build_failed` | ❌ Falha (build do Docker) |
| `update_failed` | ❌ Falha (boot da app) |
| `canceled` | ❌ Falha (cancelado manualmente) |
| `deactivated` | ❌ Falha (serviço suspenso) |

---

## 6. Parte D — Ajustes no Dockerfile

Duas alterações foram necessárias para o Render trabalhar bem com o nosso Dockerfile.

### D.1 Usar a porta dinâmica do Render

O Render injeta a variável `PORT` em runtime. O `CMD` precisa de a respeitar:

```dockerfile
CMD ["sh", "-c", "alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

- **`alembic upgrade head &&`** — aplica migrações antes da app subir (idempotente)
- **`${PORT:-8000}`** — usa `$PORT` se existir, senão `8000` (para `docker compose` local)

### D.2 Versão de Python correta

O `.python-version` do projeto pina **3.11**, e o `uv.lock` está congelado nessa versão. A imagem base **deve** ser `python:3.11-slim` (não 3.12 ou outra) — senão o `uv sync --frozen` falha com:

```
error: No interpreter found for Python 3.11
```

```dockerfile
FROM python:3.11-slim AS builder
# ...
FROM python:3.11-slim AS runtime
```

> ⚠️ **Sempre que mudares `.python-version`, muda também o `Dockerfile`.**

---

## 7. Como Testar o Pipeline

### 7.1 Primeiro deploy

```bash
# 1. Garante que estás na main e atualizado
git checkout main
git pull

# 2. Faz uma alteração pequena (ex: editar README)
echo "" >> README.md
git add README.md
git commit -m "ci: trigger first deploy"
git push origin main
```

### 7.2 Acompanhar

1. **GitHub Actions** → `https://github.com/<user>/<repo>/actions`
   - Vê o job `test` correr (~1-2 min)
   - Depois o job `deploy` (~3-8 min, dependendo do build)

2. **Render Dashboard** → serviço `helpdesk-api`
   - Vai vê o **deploy in progress**
   - Quando ficar **Live**, copia o URL público (ex: `https://helpdesk-api.onrender.com`)

3. **Smoke test**
   ```bash
   curl https://helpdesk-api.onrender.com/health
   # {"status":"healthy"}
   
   curl https://helpdesk-api.onrender.com/docs
   # (HTML do Swagger)
   ```

### 7.3 Testar um Pull Request

```bash
git checkout -b feature/teste-pr
echo "" >> README.md
git commit -am "test PR"
git push -u origin feature/teste-pr
```

1. Abre o PR no GitHub
2. Vê o job `test` correr — o `deploy` é **skipped** (correto!)
3. Aprova e faz merge → agora dispara o deploy

---

## 8. Fluxo Diário de Trabalho

```
1. git checkout -b feature/minha-feature
2. Codificar + testar localmente (uv run pytest)
3. git commit + git push
4. Abrir PR para main
5. ⏳ Esperar que CI passe (GitHub mostra ✅ no PR)
6. Pedir review se aplicável
7. Merge para main
8. ⏳ GitHub Actions corre testes + deploy automaticamente
9. Receber notificação (email/Slack) se algo falhar
10. ✅ Feature live em produção
```

---

## 9. Troubleshooting

### "Build failed" no Render

Abre o deploy no Dashboard → **Logs** → vê as últimas 50 linhas.

| Sintoma nos logs | Causa | Fix |
|------------------|-------|-----|
| `No interpreter found for Python 3.11` | Dockerfile usa Python diferente do `.python-version` | Mudar imagem base para `python:3.11-slim` |
| `unable to install package X` | `uv.lock` desatualizado | `uv lock` localmente e commit |
| `psycopg2 failed to build` | Falta `libpq-dev` no builder | Já temos — verifica não removeste |
| Timeout no build | Tier free com pouca RAM | Aguarda + retry, ou faz upgrade |

### "deploy" não corre no GitHub Actions

- Confirma que estás a fazer **push em `main`**, não em PR
- Em PRs, `deploy` é skipped por design (lê `if:` na linha do job)
- O job `test` tem que passar primeiro

### "Could not extract deploy id"

- O secret `RENDER_DEPLOY_HOOK` provavelmente está mal copiado
- Vai a Render → Settings → Deploy Hook → copia outra vez
- Atualiza o secret no GitHub

### Polling falha com 401

- O secret `RENDER_API_KEY` está errado ou expirado
- Cria nova em Account Settings → API Keys
- Atualiza no GitHub

### App sobe mas dá 502 / Bad Gateway

- A app não está a ouvir em `$PORT` — verifica o `CMD` do Dockerfile
- Vai a Render → Logs do serviço (não do deploy) e vê o erro real
- Comum: `SECRET_KEY` em falta ou < 32 chars

### Migração Alembic falha

- Render Logs mostram o erro do `alembic upgrade head`
- Local: testa `uv run alembic upgrade head` contra a tua BD local
- Se uma migração estiver corrupta, faz um `alembic downgrade -1` e cria uma nova

### Cold start lento (free tier)

- O tier free do Render **dorme após 15 min sem tráfego**
- Primeiro request pode demorar 30-60s a acordar
- Mitigação: pinga `/health` periodicamente (ex: cron-job.org) ou faz upgrade

### Quero rollback rápido

- Render Dashboard → serviço → **Events**
- Encontra um deploy anterior **live**
- Clica nos 3 pontos → **Rollback to this version**
- Não envolve git, é instantâneo

---

## 📚 Referências

- [Render Docs — Docker on Render](https://render.com/docs/docker)
- [Render Docs — Deploy Hooks](https://render.com/docs/deploy-hooks)
- [Render Docs — REST API](https://api-docs.render.com)
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [astral-sh/setup-uv](https://github.com/astral-sh/setup-uv)

---

## 🧱 Histórico das decisões deste projeto

Lições aprendidas durante o setup, para futuro reference:

1. **Auto-Deploy do Render ficou desligado** — quem controla o deploy é o GitHub Actions. Mais previsível.
2. **Python 3.11, não 3.12** — `.python-version` do projeto pina 3.11 e o `uv.lock` está congelado; mudar o Dockerfile sem mudar isto quebra o build.
3. **`UV_PYTHON_DOWNLOADS=never`** no Dockerfile — boa prática production (não queremos que o uv descarregue interpretadores ao boot do container), mas obriga a que a versão da imagem base corresponda ao `.python-version`.
4. **`alembic upgrade head` no `CMD`** — em vez de no entrypoint separado. Simples e funciona porque o Alembic é idempotente.
5. **Polling do estado do deploy** — `curl` ao webhook retorna `200` antes do build começar. Sem polling, o workflow reporta sucesso prematuramente.
6. **Repositório no mesmo region** — `helpdesk-db` e `helpdesk-api` ambos em **Frankfurt**. Cross-region latency mata performance e o Internal URL não funciona.
7. **`dependency_overrides` nos testes de API** — `get_repository()` cria uma instância nova por request; usamos override do FastAPI para partilhar estado entre requests dentro do mesmo teste.
