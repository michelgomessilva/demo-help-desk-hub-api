# 📈 Observabilidade — HelpDesk Hub API

Guia **passo a passo** ("baby steps") para perceber, configurar e validar toda a
stack de observabilidade do projeto: **logs**, **traces** e **métricas**, com
correlação direta entre eles no Grafana.

> TL;DR para quem já sabe o que faz:
> ```bash
> cp .env.example .env            # preencher SECRET_KEY
> docker compose up -d --build
> # gerar tráfego e abrir o Grafana em http://localhost:3001 (admin/admin)
> ```

---

## Índice

1. [O que é observabilidade (os 3 pilares)](#1-o-que-é-observabilidade-os-3-pilares)
2. [Como cobrimos o projeto inteiro sem o modificar inteiro](#2-como-cobrimos-o-projeto-inteiro-sem-o-modificar-inteiro)
3. [Arquitetura da solução](#3-arquitetura-da-solução)
4. [O que foi alterado no código](#4-o-que-foi-alterado-no-código)
5. [Pré-requisitos](#5-pré-requisitos)
6. [Passo 1 — Variáveis de ambiente](#passo-1--variáveis-de-ambiente)
7. [Passo 2 — Subir a stack](#passo-2--subir-a-stack)
8. [Passo 3 — Validar os health checks](#passo-3--validar-os-health-checks)
9. [Passo 4 — Gerar tráfego](#passo-4--gerar-tráfego)
10. [Passo 5 — Ver LOGS no Grafana (Loki)](#passo-5--ver-logs-no-grafana-loki)
11. [Passo 6 — Ver TRACES no Grafana (Tempo)](#passo-6--ver-traces-no-grafana-tempo)
12. [Passo 7 — Correlação LOG ↔ TRACE](#passo-7--correlação-log--trace)
13. [Passo 8 — Ver MÉTRICAS no Grafana (Prometheus)](#passo-8--ver-métricas-no-grafana-prometheus)
14. [Graceful degradation (correr sem a stack)](#10-graceful-degradation-correr-sem-a-stack)
15. [Troubleshooting](#11-troubleshooting)
16. [Como replicar isto noutro projeto (do zero)](#12-como-replicar-isto-noutro-projeto-do-zero)
17. [Mapa de alterações detalhado (ficheiros e linhas)](#13-mapa-de-alterações-detalhado-ficheiros-e-linhas)

---

## 1. O que é observabilidade (os 3 pilares)

| Pilar | Pergunta que responde | Ferramenta usada aqui |
|-------|-----------------------|-----------------------|
| **Logs** | "O que aconteceu?" (eventos discretos) | **Loki** |
| **Traces** | "Por onde passou o pedido e quanto demorou cada passo?" | **Tempo** |
| **Métricas** | "Quantos? Quão rápido? Com que frequência?" (agregados) | **Prometheus** |

Tudo é visualizado num só sítio: o **Grafana**.

O segredo da observabilidade moderna é a **correlação**: a partir de um log
conseguir saltar para o trace exato daquele pedido, e vice-versa. Isto é feito
injetando o `trace_id`/`span_id` em cada log.

---

## 2. Como cobrimos o projeto inteiro sem o modificar inteiro

A pergunta mais importante de toda esta implementação é:

> *"Como é que se mede **cada** pedido HTTP e **cada** query à base de dados sem
> ter de mexer em todas as rotas e em todos os repositórios?"*

A resposta é **auto-instrumentação** (monkey-patching em runtime) + **propagação
implícita de contexto**. É isto que permite cobrir o projeto **inteiro** mexendo
apenas em ~4 ficheiros.

### A ideia numa frase

Não instrumentamos o código rota a rota. **Embrulhamos o framework.** Numa única
chamada, o OpenTelemetry substitui (em memória, no arranque) os métodos internos
do FastAPI e do SQLAlchemy por versões que medem o tempo e criam *spans*. Por
isso cada pedido HTTP e cada query passa a ser observada **sem tocar em nenhuma
rota nem repositório**.

### Os 4 mecanismos

**1. Auto-instrumentação = *monkey-patching* no arranque.** Estas duas linhas em
[observability.py:120](src/infrastructure/observability.py#L120) e
[:125](src/infrastructure/observability.py#L125) fazem o trabalho todo:

```python
FastAPIInstrumentor.instrument_app(app)               # embrulha o middleware HTTP
SQLAlchemyInstrumentor().instrument(engine=engine)    # embrulha a execução de queries
```

Por baixo, o instrumentor **troca em tempo de execução** funções internas do
framework por *wrappers* que fazem, em essência:
`span = start_span(); executa_o_original(); span.end()`. Como **todo** o tráfego
HTTP passa pelo middleware do FastAPI e **toda** a query passa pelo engine do
SQLAlchemy, instrumentar esses dois pontos cobre 100% da aplicação. A lógica de
negócio nem sabe que está a ser medida.

> 🔌 **Analogia:** não pões um cronómetro em cada funcionário; pões um sensor na
> **porta de entrada** e na **porta da base de dados**. Toda a gente passa por lá.

**2. Propagação implícita de contexto (`contextvars`).** *"Como é que a query SQL
sabe a que pedido HTTP pertence?"* — sem lhe passarmos nada. O OTel mantém o
**"span atual"** num `contextvar` (variável de contexto por tarefa). Quando o
wrapper do FastAPI abre o span do pedido, este torna-se o "span atual"; quando,
mais abaixo na pilha de chamadas, o SQLAlchemy abre o span da query, ele lê o
"span atual" e **liga-se a ele como filho** — automaticamente. É assim que se
constrói a *waterfall* (HTTP → query1 → query2) sem ninguém passar IDs à mão.

**3. A única alteração transversal: correlacionar logs com traces.** Traces e
métricas saem "de graça" da auto-instrumentação. Os **logs** são o único sítio que
precisou de uma alteração — e mínima: **+1 linha** na pipeline do structlog
([logging_config.py:82-83](src/infrastructure/logging_config.py#L82-L83)):

```python
add_trace_context,   # injeta trace_id/span_id no log
```

Esse processor ([observability.py:144-168](src/infrastructure/observability.py#L144-L168))
**também não recebe nada**: vai buscar o "span atual" ao mesmo `contextvar`
(`trace.get_current_span()`) e copia o `trace_id`/`span_id` para o log. Por isso,
nem a correlação log↔trace exige passar IDs pelo código.

**4. Um único ponto de entrada + módulo isolado.** Tudo é ligado **uma vez**, na
fábrica da app ([main.py:151-161](src/main.py#L151-L161)):

```python
configure_observability(app, engine=engine)
```

Toda a complexidade (providers, exporters, instrumentação) vive **dentro de um só
módulo** (`observability.py`). O resto do projeto **não importa OpenTelemetry em
lado nenhum**. Para remover a observabilidade, apagas o módulo e esta chamada — e
mais nada.

### Por isso a "pegada" no código é tão pequena

| O que querias observar | O que tiveste de escrever |
|------------------------|---------------------------|
| Todos os pedidos HTTP | 1 linha (`instrument_app`) |
| Todas as queries à BD | 1 linha (`instrument(engine)`) |
| Métricas de latência/contagem | 0 linhas (vêm da mesma instrumentação) |
| `trace_id` em cada log | 1 linha na pipeline + 1 processor isolado |
| Ligar tudo | 1 chamada na fábrica da app |

O "trabalho pesado" não está no código Python — está na **configuração externa**
(`docker-compose.yml` + `observability/*.yaml`), que é declarativa e não toca na
aplicação. A app só conhece **um endereço**: o do Collector
([observability.py:76](src/infrastructure/observability.py#L76)). Quem distribui
para Loki/Tempo/Prometheus é o Collector — *desacoplamento total* (ver
[Arquitetura](#3-arquitetura-da-solução)).

---

## 3. Arquitetura da solução

```
                          ┌──────────────────────────────────────────┐
                          │           OpenTelemetry Collector          │
                          │  (ponto central — recebe e distribui)      │
   ┌────────────┐  OTLP   │                                            │
   │            │ traces  │  receivers:                                │
   │  FastAPI   ├────────►│   - otlp (http :4318 / grpc :4317)         │
   │   (API)    │ métricas│   - filelog (lê logs/app.jsonl)            │
   │            │         │                                            │
   └─────┬──────┘         │  exporters:                                │
         │                │   - otlp/tempo   ──► Tempo   (traces)      │
         │ escreve        │   - prometheus   ──► :8889   (métricas)    │
         ▼                │   - otlphttp/loki ─► Loki    (logs)        │
   logs/app.jsonl ───────►│                                            │
   (structlog JSON)       └───────┬─────────────┬──────────────┬───────┘
                                  │             │              │
                                  ▼             ▼              ▼
                               ┌──────┐     ┌────────┐    ┌────────────┐
                               │ Tempo│     │  Loki  │    │ Prometheus │
                               └───┬──┘     └───┬────┘    └─────┬──────┘
                                   └────────────┼───────────────┘
                                                ▼
                                          ┌──────────┐
                                          │ Grafana  │  http://localhost:3001
                                          └──────────┘
```

Pontos-chave:
- A aplicação **só conhece o Collector** (`OTEL_EXPORTER_OTLP_ENDPOINT`). Não sabe
  nada de Loki/Tempo/Prometheus — o Collector é que distribui. Isto é
  desacoplamento.
- Os **logs não foram reescritos**: o `structlog` continua a escrever JSON em
  `logs/app.jsonl`; o Collector limita-se a ler esse ficheiro (receiver `filelog`).

---

## 4. O que foi alterado no código

| Ficheiro | Alteração |
|----------|-----------|
| `pyproject.toml` | + dependências `opentelemetry-*` (via `uv add`) |
| `src/infrastructure/observability.py` | **NOVO** — inicializa traces+métricas, instrumenta FastAPI/SQLAlchemy, e fornece o processor `add_trace_context` |
| `src/infrastructure/logging_config.py` | **+1 linha** na pipeline de processors: `add_trace_context` (injeta `trace_id`/`span_id`). Nada mais mudou |
| `src/main.py` | chama `configure_observability(app, engine)` dentro de `create_app()` |
| `src/api/routes/system_routes.py` | + `/health/live` (liveness) e `/health/ready` (readiness com `SELECT 1`) |
| `src/api/schemas/responses/health_response.py` | + `ReadinessResponse` |
| `docker-compose.yml` | + serviços `otel-collector`, `loki`, `tempo`, `prometheus`, `grafana` + env OTEL na `api` |
| `observability/*` | **NOVO** — ficheiros de configuração de cada serviço |
| `.env.example` | + variáveis `OTEL_*` |

**Princípios respeitados:** sem hardcode (tudo via env), graceful degradation
(app funciona sem a stack), módulo isolado, lógica de logs intacta.

---

## 5. Pré-requisitos

- **Docker** + **Docker Compose** (v2: comando `docker compose`).
- **uv** (apenas se quiseres correr a app fora do Docker).
- Portas livres no host: `8000` (api), `5432` (postgres), `3001` (grafana),
  `3100` (loki), `3200` (tempo), `9090` (prometheus), `4317`/`4318`/`8889` (collector).

---

## Passo 1 — Variáveis de ambiente

1. Copia o exemplo:
   ```bash
   cp .env.example .env
   ```
2. Preenche a `SECRET_KEY` (obrigatória, 32+ caracteres):
   ```bash
   # Linux/macOS
   openssl rand -hex 32
   # Windows PowerShell
   -join ((48..57) + (97..102) | Get-Random -Count 64 | ForEach-Object {[char]$_})
   ```
3. Confirma as variáveis de observabilidade no `.env`:
   ```env
   OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318   # ver nota abaixo
   OTEL_SERVICE_NAME=helpdesk-hub-api
   OTEL_SDK_DISABLED=false
   ```

> ℹ️ **Nota importante sobre o endpoint:**
> - Quando corres **tudo via docker compose**, o `docker-compose.yml` já define
>   automaticamente `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318` para o
>   container da API (sobrepõe o do `.env`). Não precisas mexer.
> - O valor `http://localhost:4318` no `.env` serve para quando corres a **API fora
>   do Docker** (`uv run uvicorn ...`) contra a stack que está no Docker.

---

## Passo 2 — Subir a stack

```bash
docker compose up -d --build
```

Confirma que todos os serviços estão de pé:

```bash
docker compose ps
```

Deves ver: `helpdesk_api`, `helpdesk_postgres`, `helpdesk_otel_collector`,
`helpdesk_loki`, `helpdesk_tempo`, `helpdesk_prometheus`, `helpdesk_grafana`.

Para ver os logs de arranque de um serviço (ex.: a API ou o collector):

```bash
docker compose logs -f api
docker compose logs -f otel-collector
```

Na API, deves ver o log `observability_initialized`.

---

## Passo 3 — Validar os health checks

```bash
# Liveness (a app está viva?) -> 200 {"status":"healthy"}
curl http://localhost:8000/health
curl http://localhost:8000/health/live

# Readiness (a app está pronta? valida a BD) -> 200 {"status":"ready",...}
curl http://localhost:8000/health/ready
```

Testar o cenário de falha (readiness deve dar **503**):

```bash
docker compose stop postgres
curl -i http://localhost:8000/health/ready    # -> HTTP/1.1 503 ... "database":"error: ..."
docker compose start postgres
```

| Endpoint | Significado | Uso típico |
|----------|-------------|------------|
| `/health`, `/health/live` | **Liveness** — processo vivo | reinício de container (Docker/K8s) |
| `/health/ready` | **Readiness** — pronto p/ tráfego (BD OK) | balanceador/ingress decide enviar tráfego |

---

## Passo 4 — Gerar tráfego

Para haver dados para ver, faz alguns pedidos:

```bash
curl http://localhost:8000/
curl http://localhost:8000/categories

# registar + login (gera traces que passam pela BD)
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Ana","email":"ana@example.com","password":"password123"}'

curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ana@example.com","password":"password123"}'
```

> As métricas são exportadas a cada ~60s e o Prometheus faz scrape a cada 15s, por
> isso dá ~1 minuto antes de aparecerem.

### Tráfego contínuo (recomendado) — `scripts/load-test.ps1`

Para ter dados ricos e realistas (vários utilizadores, tickets, comentários,
filtros, e até 404s de propósito), corre o simulador de carga em **PowerShell**.
Ele gera tráfego **indefinidamente** até parares com `Ctrl+C`:

```powershell
# A partir da raiz do projeto, com a API a responder em http://localhost:8000
./scripts/load-test.ps1

# Mais intenso (menos pausa entre pedidos)
./scripts/load-test.ps1 -MinDelayMs 50 -MaxDelayMs 200

# Apontar para outra instância
./scripts/load-test.ps1 -BaseUrl http://localhost:8000
```

Cada pedido é mostrado com cor por código de status e é impresso um resumo
periódico (e um resumo final ao parar). Para **mais carga**, abre vários
terminais e corre o script em cada um.

---

## Passo 5 — Ver LOGS no Grafana (Loki)

1. Abre **http://localhost:3001** (login `admin` / `admin` — ou entra como anónimo).
2. Menu lateral → **Explore**.
3. No topo, escolhe o datasource **Loki**.
4. Query (modo código):
   ```logql
   {service_name="helpdesk-hub-api"}
   ```
5. Clica **Run query**. Vês as linhas JSON dos logs, cada uma com `trace_id`,
   `span_id`, `method`, `path`, `status_code`, etc.

Exemplos de filtro:
```logql
{service_name="helpdesk-hub-api"} | json | level="error"
{service_name="helpdesk-hub-api"} |= "HTTP Request"
```

---

## Passo 6 — Ver TRACES no Grafana (Tempo)

1. **Explore** → datasource **Tempo**.
2. Separador **Search** → escolhe o **Service Name** `helpdesk-hub-api` → **Run query**.
3. Clica num trace. Vês a *waterfall* de spans:
   - span do **FastAPI** (o pedido HTTP),
   - spans do **SQLAlchemy** (cada query à BD), com a duração de cada um.

---

## Passo 7 — Correlação LOG ↔ TRACE

Esta é a parte mais valiosa. **De um log salta-se para o trace exato.**

1. Em **Explore → Loki**, corre `{service_name="helpdesk-hub-api"}`.
2. Expande uma linha de log (clica nela).
3. No campo **TraceID** (derived field configurado automaticamente) aparece um botão
   **"Tempo"** → clica.
4. O Grafana abre o **trace correspondente** no Tempo, no mesmo ecrã.

E no sentido inverso (trace → logs): num trace aberto no Tempo, usa o botão
**"Logs for this span"** (configurado via `tracesToLogs`).

> Como funciona: o `structlog` inclui `"trace_id":"<hex>"` em cada log; o datasource
> Loki tem um *derived field* com a regex `"trace_id":\s*"([a-f0-9]+)"` que
> transforma esse valor num link para o Tempo. Ver `observability/grafana/datasources.yaml`.

---

## Passo 8 — Ver MÉTRICAS no Grafana (Prometheus)

1. **Explore** → datasource **Prometheus**.
2. Exemplos de queries (métricas geradas pela instrumentação FastAPI):
   ```promql
   # contagem de pedidos HTTP
   http_server_duration_milliseconds_count

   # latência (p95) por rota — requer histograma
   histogram_quantile(0.95, sum(rate(http_server_duration_milliseconds_bucket[5m])) by (le, http_route))
   ```
3. Podes confirmar os *targets* do Prometheus em **http://localhost:9090/targets**
   (devem estar `UP`: `otel-collector:8889` e `otel-collector:8888`).

> Os nomes exatos das métricas dependem da versão da instrumentação. Em **Explore →
> Prometheus**, usa o *Metrics browser* para listar tudo o que começa por
> `http_server_`.

---

## 10. Graceful degradation (correr sem a stack)

A aplicação **nunca depende** da observabilidade para funcionar.

- **Desligar só a monitorização** (a API continua a responder):
  ```bash
  docker compose stop otel-collector loki tempo prometheus grafana
  curl http://localhost:8000/health      # continua 200
  ```
  Os logs continuam a ser escritos em `logs/app.jsonl`. O exportador OTLP apenas
  regista um aviso de "transient error" e tenta reenviar — não quebra nada.

- **Desligar a telemetria por completo** (nem tenta exportar):
  ```env
  OTEL_SDK_DISABLED=true
  ```
  ou deixar `OTEL_EXPORTER_OTLP_ENDPOINT` vazio. No arranque verás o log
  `observability_disabled`.

Isto está implementado em `src/infrastructure/observability.py` (função
`_is_disabled()` + `try/except` em toda a inicialização).

---

## 11. Troubleshooting

| Sintoma | Causa provável / solução |
|---------|--------------------------|
| Não aparecem logs no Loki | A API ainda não escreveu nada → gera tráfego (Passo 4). Confirma que `./logs/app.jsonl` existe e que o `otel-collector` o monta (`docker compose logs otel-collector`). |
| Não aparecem traces no Tempo | Confirma `OTEL_EXPORTER_OTLP_ENDPOINT` na API e os logs do collector. Verifica que o exportador `otlp/tempo` aponta para `tempo:4317`. |
| Métricas vazias no Prometheus | Esperar ~1 min (intervalo de export). Ver **http://localhost:9090/targets** — devem estar `UP`. |
| `/health/ready` dá 503 | A BD não está acessível. `docker compose ps postgres` e ver logs do postgres. |
| Link TraceID não aparece no log | O log foi emitido **fora** de um pedido HTTP (sem span ativo) — só pedidos têm `trace_id`. |
| Porta 3000 ocupada | O Grafana está mapeado para **3001** no host de propósito (3000 fica para a frontend). |
| `grpcio`/instalação no Windows | Usamos o exportador **OTLP/HTTP** (`opentelemetry-exporter-otlp-proto-http`), que **não** precisa de `grpcio` compilado. |

Comandos úteis:
```bash
docker compose ps
docker compose logs -f otel-collector
docker compose logs -f api
docker compose down            # parar tudo (mantém volumes)
docker compose down -v         # parar tudo e APAGAR dados (loki/tempo/prometheus/grafana/postgres)
```

---

## 12. Como replicar isto noutro projeto (do zero)

Resumo reproduzível da implementação:

1. **Instalar dependências** (com `uv`):
   ```bash
   uv add opentelemetry-api opentelemetry-sdk \
          opentelemetry-exporter-otlp-proto-http \
          opentelemetry-instrumentation-fastapi \
          opentelemetry-instrumentation-sqlalchemy
   ```
2. **Criar `observability.py`** com:
   - `configure_observability(app, engine)`: cria `Resource`, `TracerProvider` +
     `BatchSpanProcessor` (OTLP), `MeterProvider` + `PeriodicExportingMetricReader`
     (OTLP), e instrumenta FastAPI + SQLAlchemy. Tudo dentro de `try/except` e com
     *early return* se a telemetria estiver desligada.
   - `add_trace_context(...)`: processor que injeta `trace_id`/`span_id`.
3. **Enriquecer o logging** já existente: adicionar `add_trace_context` à pipeline de
   processors do structlog (sem tocar no resto).
4. **Chamar `configure_observability(app, engine)`** na factory da app.
5. **Criar os health checks** `/health/live` e `/health/ready` (este com `SELECT 1`).
6. **docker-compose**: adicionar `otel-collector`, `loki`, `tempo`, `prometheus`,
   `grafana` e passar as env `OTEL_*` à aplicação.
7. **Ficheiros de config** em `observability/`:
   - `otel-collector-config.yaml` (receivers otlp+filelog → exporters tempo/prometheus/loki),
   - `loki-config.yaml`, `tempo.yaml`, `prometheus.yml`,
   - `grafana/datasources.yaml` (datasources + correlação log↔trace).
8. **Validar** (Passos 2–8 deste documento).

---

## 13. Mapa de alterações detalhado (ficheiros e linhas)

Esta secção lista **todos** os ficheiros tocados pela implementação da
observabilidade (commit `9f72c5d`), distinguindo **ficheiros novos** de
**ficheiros modificados** e apontando, nos modificados, as **linhas** onde se
mexeu. Resumo do commit: **17 ficheiros**, **+1927 / −13 linhas**.

> As linhas indicadas referem-se ao estado **após** o commit. Para ver o diff
> exato a qualquer momento:
> ```bash
> git show 9f72c5d -- <ficheiro>     # diff de um ficheiro
> git show 9f72c5d --stat            # resumo de todos
> ```

### 13.1 Ficheiros NOVOS

| Ficheiro | Linhas | Conteúdo |
|----------|:------:|----------|
| `src/infrastructure/observability.py` | 168 | Módulo central: `configure_observability(app, engine)` (traces + métricas, instrumentação FastAPI/SQLAlchemy), `add_trace_context` (injeta `trace_id`/`span_id`) e `_is_disabled()` (graceful degradation). |
| `observability/otel-collector-config.yaml` | 82 | Config do OpenTelemetry Collector: receivers `otlp` + `filelog`; exporters `otlp/tempo`, `prometheus`, `otlphttp/loki`. |
| `observability/grafana/datasources.yaml` | 59 | Datasources Loki/Tempo/Prometheus + correlação log↔trace (derived fields / `tracesToLogs`). |
| `observability/loki-config.yaml` | 44 | Config do Loki (armazenamento de logs). |
| `observability/tempo.yaml` | 33 | Config do Tempo (armazenamento de traces). |
| `observability/prometheus.yml` | 24 | Config do Prometheus (scrape do collector em `:8889`/`:8888`). |
| `scripts/load-test.ps1` | 420 | Simulador de carga em PowerShell (tráfego contínuo realista). |

### 13.2 Ficheiros MODIFICADOS

| Ficheiro | Linhas alteradas | O que mudou |
|----------|------------------|-------------|
| `src/main.py` | **+151–161** | Bloco `try/except` em `create_app()` que chama `configure_observability(app, engine=engine)` (graceful: ignora se a stack estiver desligada). |
| `src/infrastructure/logging_config.py` | **+60–62** (import tardio de `add_trace_context`); **+82–83** (processor na pipeline do structlog) | Injeta `trace_id`/`span_id` nos logs. Renumeração dos comentários 3→5. Nada mais mudou na lógica de logs. |
| `src/api/routes/system_routes.py` | **2–3, 6–7** (imports `JSONResponse`, `text`, `ReadinessResponse`, `engine`); **+29–69** (docstring de `/health`, novos `/health/live` e `/health/ready`) | Adiciona liveness explícito e readiness com `SELECT 1` (200/503). |
| `src/api/schemas/responses/health_response.py` | **+10–18** | Novo schema `ReadinessResponse` (`status` + `checks: dict[str, str]`); docstrings em `HealthResponse`. |
| `src/infrastructure/di/dependencies.py` | **30, 32–34** (imports); **43–60** (`get_repository`) | Troca `InMemoryTicketRepository` → `SQLAlchemyTicketRepository` com sessão injetada via `Depends(get_db_session)`. ⚠️ Mudança de persistência incluída no mesmo commit. |
| `docker-compose.yml` | **+35–36, +52–64, +70–182** (3 hunks) | Env `OTEL_*` no serviço `api` + novos serviços `otel-collector`, `loki`, `tempo`, `prometheus`, `grafana`. |
| `pyproject.toml` | **+12–16** | 5 dependências `opentelemetry-*` (api, sdk, exporter-otlp-proto-http, instrumentation-fastapi, instrumentation-sqlalchemy). |
| `.env.example` | **+27–39** | Bloco de variáveis `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME`, `OTEL_SDK_DISABLED`. |
| `uv.lock` | **+503** | Lockfile regenerado pelo `uv add` (não editar à mão). |
| `OBSERVABILITY.md` | **novo (374) → atualizado** | Este documento. |

---

### Referências
- OpenTelemetry Python: https://opentelemetry.io/docs/languages/python/
- OTel Collector: https://opentelemetry.io/docs/collector/
- Grafana Loki (OTLP): https://grafana.com/docs/loki/latest/send-data/otel/
- Grafana Tempo: https://grafana.com/docs/tempo/latest/
- Correlação Loki ↔ Tempo (derived fields): https://grafana.com/docs/grafana/latest/datasources/loki/#derived-fields
