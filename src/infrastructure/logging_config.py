"""
Configuração de logging estruturado com Structlog.

Logs em JSON estruturado são salvos em arquivo (logs/app.jsonl):
- Cada linha é um evento JSON completo
- Mantém histórico para análise posterior
- Também exibe no console em tempo real

Uso:
    from src.infrastructure.logging_config import configure_structlog, get_logger

    configure_structlog()
    logger = get_logger(__name__)
    logger.info("evento", user_id=123)

Consultar logs:
    # Últimos logs
    tail -f logs/app.jsonl | jq .

    # Filtrar por nível
    grep '"level":"error"' logs/app.jsonl | jq .

    # Filtrar por evento
    grep 'user_registered' logs/app.jsonl | jq .
"""

import structlog
import logging
from pathlib import Path
import os
import sys

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOGS_DIR = Path("logs")


class FileAndConsoleRenderer:
    """Renderizador que escreve em arquivo E console simultaneamente."""

    def __call__(self, logger, name: str, event_dict: dict) -> str:
        # Usar o JSONRenderer padrão
        json_renderer = structlog.processors.JSONRenderer()
        json_str = json_renderer(logger, name, event_dict)

        # Salvar em arquivo
        try:
            LOGS_DIR.mkdir(exist_ok=True)
            with open(LOGS_DIR / "app.jsonl", "a", encoding="utf-8") as f:
                f.write(json_str + "\n")
                f.flush()
        except Exception:
            pass

        return json_str


def configure_structlog() -> None:
    """Configura logging estruturado com Structlog."""

    # Configurar logging padrão do Python
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, LOG_LEVEL),
        stream=sys.stdout,
    )

    # Configurar Structlog
    structlog.configure(
        processors=[
            # 1. Adiciona timestamp
            structlog.processors.TimeStamper(fmt="iso"),

            # 2. Adiciona nível de log
            structlog.processors.add_log_level,

            # 3. Processa exceptions
            structlog.processors.StackInfoRenderer(),
            structlog.processors.ExceptionRenderer(),

            # 4. Renderiza como JSON e salva em arquivo
            FileAndConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Retorna um logger estruturado."""
    if name is None:
        name = __name__

    return structlog.get_logger(name)
