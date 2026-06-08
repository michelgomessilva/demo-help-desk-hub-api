"""
Inicialização do OpenTelemetry (Traces + Métricas) e correlação de logs.

Este módulo concentra TODA a configuração de observabilidade da aplicação,
mantendo o resto do código limpo e desacoplado.

Pilares cobertos:
- Traces  -> exportados via OTLP/HTTP para o OpenTelemetry Collector
- Métricas -> exportadas via OTLP/HTTP para o OpenTelemetry Collector
- Logs    -> NÃO são reescritos aqui. Apenas enriquecemos os logs estruturados
             existentes (structlog) com `trace_id`/`span_id` através do processor
             `add_trace_context`, garantindo correlação direta logs <-> traces.

Princípios de design:
- Graceful degradation: se a stack de observabilidade estiver desligada ou se
  `OTEL_EXPORTER_OTLP_ENDPOINT` não estiver definido, a aplicação continua a
  funcionar normalmente. Nenhuma falha de telemetria pode quebrar a app.
- Sem hardcode: endpoint, nome do serviço e ambiente vêm de variáveis de ambiente.

Variáveis de ambiente relevantes:
- OTEL_EXPORTER_OTLP_ENDPOINT : endpoint base do Collector (ex: http://otel-collector:4318).
                                Se vazio, a telemetria é desativada.
- OTEL_SERVICE_NAME           : nome do serviço (default: helpdesk-hub-api).
- OTEL_SDK_DISABLED           : "true" desliga totalmente a telemetria (standard OTel).
- ENVIRONMENT                 : ambiente de deployment (development/production/...).
"""

from __future__ import annotations

import os
from typing import Any

from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__)

# Flag interna para sabermos se o SDK foi inicializado com sucesso.
# Usada apenas para evitar dupla inicialização.
_initialized = False


def _is_disabled() -> bool:
    """Telemetria desativada se OTEL_SDK_DISABLED=true ou endpoint não configurado."""
    if os.getenv("OTEL_SDK_DISABLED", "false").strip().lower() == "true":
        return True
    if not os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip():
        return True
    return False


def configure_observability(app: Any, engine: Any | None = None) -> None:
    """
    Configura Traces e Métricas do OpenTelemetry e instrumenta FastAPI/SQLAlchemy.

    É seguro chamar mesmo sem a stack ligada: nesse caso, faz `return` cedo.
    Qualquer erro durante a inicialização é capturado e apenas registado — a
    aplicação nunca é interrompida por causa da telemetria.

    Args:
        app: instância FastAPI a instrumentar.
        engine: engine SQLAlchemy a instrumentar (opcional).
    """
    global _initialized

    if _initialized:
        logger.debug("observability_already_initialized")
        return

    if _is_disabled():
        logger.info(
            "observability_disabled",
            reason="OTEL_EXPORTER_OTLP_ENDPOINT não definido ou OTEL_SDK_DISABLED=true",
        )
        return

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip().rstrip("/")
    service_name = os.getenv("OTEL_SERVICE_NAME", "helpdesk-hub-api")
    environment = os.getenv("ENVIRONMENT", "development")

    try:
        from opentelemetry import metrics, trace
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # Recurso: identifica o serviço em todos os sinais (traces/métricas).
        resource = Resource.create(
            {
                "service.name": service_name,
                "service.version": "1.0.0",
                "deployment.environment": environment,
            }
        )

        # ---- Traces ----------------------------------------------------------
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"))
        )
        trace.set_tracer_provider(tracer_provider)

        # ---- Métricas --------------------------------------------------------
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics")
        )
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)

        # ---- Instrumentação automática --------------------------------------
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)

        if engine is not None:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

            SQLAlchemyInstrumentor().instrument(engine=engine)

        _initialized = True
        logger.info(
            "observability_initialized",
            service_name=service_name,
            environment=environment,
            endpoint=endpoint,
            signals=["traces", "metrics"],
        )

    except Exception as exc:  # noqa: BLE001 - telemetria nunca pode quebrar a app
        logger.warning(
            "observability_init_failed",
            error=str(exc),
            note="A aplicação continua a funcionar sem telemetria.",
        )


def add_trace_context(logger: Any, method_name: str, event_dict: dict) -> dict:
    """
    Processor structlog que injeta `trace_id` e `span_id` no log.

    Permite correlacionar cada linha de log com o trace correspondente no Tempo.
    Se não houver span ativo (ou se o OTel não estiver instalado/ativo), devolve
    o `event_dict` inalterado — totalmente graceful.

    Formato:
    - trace_id: 32 dígitos hexadecimais (formato W3C trace context)
    - span_id : 16 dígitos hexadecimais
    """
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx is not None and ctx.is_valid:
            event_dict["trace_id"] = format(ctx.trace_id, "032x")
            event_dict["span_id"] = format(ctx.span_id, "016x")
    except Exception:
        # Sem OTel ou sem span ativo: não enriquecemos, mas nunca falhamos.
        pass

    return event_dict
