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
2. [Arquitetura da solução](#2-arquitetura-da-solução)
3. [O que foi alterado no código](#3-o-que-foi-alterado-no-código)
4. [Pré-requisitos](#4-pré-requisitos)
5. [Passo 1 — Variáveis de ambiente](#passo-1--variáveis-de-ambiente)
6. [Passo 2 — Subir a stack](#passo-2--subir-a-stack)
7. [Passo 3 — Validar os health checks](#passo-3--validar-os-health-checks)
8. [Passo 4 — Gerar tráfego](#passo-4--gerar-tráfego)
9. [Passo 5 — Ver LOGS no Grafana (Loki)](#passo-5--ver-logs-no-grafana-loki)
10. [Passo 6 — Ver TRACES no Grafana (Tempo)](#passo-6--ver-traces-no-grafana-tempo)
11. [Passo 7 — Correlação LOG ↔ TRACE](#passo-7--correlação-log--trace)
12. [Passo 8 — Ver MÉTRICAS no Grafana (Prometheus)](#passo-8--ver-métricas-no-grafana-prometheus)
13. [Graceful degradation (correr sem a stack)](#9-graceful-degradation-correr-sem-a-stack)
14. [Troubleshooting](#10-troubleshooting)
15. [Como replicar isto noutro projeto (do zero)](#11-como-replicar-isto-noutro-projeto-do-zero)

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

## 2. Arquitetura da solução

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

## 3. O que foi alterado no código

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

## 4. Pré-requisitos

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

## 9. Graceful degradation (correr sem a stack)

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

## 10. Troubleshooting

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

## 11. Como replicar isto noutro projeto (do zero)

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

### Referências
- OpenTelemetry Python: https://opentelemetry.io/docs/languages/python/
- OTel Collector: https://opentelemetry.io/docs/collector/
- Grafana Loki (OTLP): https://grafana.com/docs/loki/latest/send-data/otel/
- Grafana Tempo: https://grafana.com/docs/tempo/latest/
- Correlação Loki ↔ Tempo (derived fields): https://grafana.com/docs/grafana/latest/datasources/loki/#derived-fields
