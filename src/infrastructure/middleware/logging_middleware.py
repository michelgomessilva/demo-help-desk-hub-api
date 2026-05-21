"""
Middleware que loga todas as requisições e respostas HTTP.

Este middleware captura informações relevantes sobre cada requisição:
- Método HTTP (GET, POST, etc)
- Caminho da requisição
- Código de status da resposta
- Tempo de processamento
- IP do cliente

Todos os dados são estruturados em JSON e salvos em logs/app.jsonl.
"""

import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import structlog

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware que loga informações detalhadas sobre cada requisição HTTP.

    Campos capturados:
    - method: GET, POST, PUT, DELETE, etc
    - path: /api/tickets, /api/users, etc
    - status_code: 200, 404, 500, etc
    - duration_ms: tempo de processamento em milissegundos
    - client_ip: IP de origem da requisição

    Uso:
        app.add_middleware(LoggingMiddleware)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Processa a requisição, captura informações e loga estruturado.

        Args:
            request: Objeto da requisição FastAPI
            call_next: Função para processar a requisição no próximo middleware

        Returns:
            Response: Resposta HTTP (modificada ou original)
        """
        # Capturar informações da requisição
        start_time = time.time()
        path = request.url.path
        method = request.method
        query_string = request.url.query or ""
        client_ip = request.client.host if request.client else "unknown"

        # Tentar obter user_id do token (opcional)
        user_id = self._extract_user_id(request)

        try:
            # Processar a requisição
            response = await call_next(request)
            duration_ms = round((time.time() - start_time) * 1000, 2)

            # Log de sucesso
            self._log_success(
                method=method,
                path=path,
                query_string=query_string,
                status_code=response.status_code,
                duration_ms=duration_ms,
                client_ip=client_ip,
                user_id=user_id,
            )

            return response

        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)

            # Log de erro
            self._log_error(
                method=method,
                path=path,
                query_string=query_string,
                duration_ms=duration_ms,
                client_ip=client_ip,
                user_id=user_id,
                error=str(e),
            )

            raise

    @staticmethod
    def _log_success(
        method: str,
        path: str,
        query_string: str,
        status_code: int,
        duration_ms: float,
        client_ip: str,
        user_id: int = None,
    ) -> None:
        """
        Loga uma requisição bem-sucedida.

        Args:
            method: Método HTTP
            path: Caminho da requisição
            query_string: Query string (parametros na URL)
            status_code: Código de status HTTP
            duration_ms: Duração em milissegundos
            client_ip: IP do cliente
            user_id: ID do usuário (se autenticado)
        """
        # Determinar nível de log baseado no status code
        if status_code < 300:
            log_level = "info"
        elif status_code < 400:
            log_level = "info"
        elif status_code < 500:
            log_level = "warning"
        else:
            log_level = "error"

        log_data = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "client_ip": client_ip,
        }

        # Adicionar query string se não vazia
        if query_string:
            log_data["query_string"] = query_string

        # Adicionar user_id se autenticado
        if user_id:
            log_data["user_id"] = user_id

        # Usar o nível apropriado
        if log_level == "info":
            logger.info("HTTP Request", **log_data)
        elif log_level == "warning":
            logger.warning("HTTP Request", **log_data)
        else:
            logger.error("HTTP Request", **log_data)

    @staticmethod
    def _log_error(
        method: str,
        path: str,
        query_string: str,
        duration_ms: float,
        client_ip: str,
        user_id: int = None,
        error: str = None,
    ) -> None:
        """
        Loga uma requisição que resultou em erro.

        Args:
            method: Método HTTP
            path: Caminho da requisição
            query_string: Query string (parametros na URL)
            duration_ms: Duração em milissegundos
            client_ip: IP do cliente
            user_id: ID do usuário (se autenticado)
            error: Mensagem de erro
        """
        log_data = {
            "method": method,
            "path": path,
            "duration_ms": duration_ms,
            "client_ip": client_ip,
            "error": error,
        }

        if query_string:
            log_data["query_string"] = query_string

        if user_id:
            log_data["user_id"] = user_id

        logger.error("HTTP Request Error", **log_data)

    @staticmethod
    def _extract_user_id(request: Request) -> int:
        """
        Tenta extrair user_id do token JWT no header Authorization.

        Args:
            request: Objeto da requisição

        Returns:
            user_id se conseguir extrair, None caso contrário
        """
        try:
            # Procurar por Authorization header
            auth_header = request.headers.get("authorization", "")

            if not auth_header.startswith("Bearer "):
                return None

            # Extrair token
            token = auth_header.replace("Bearer ", "")

            # Decodificar JWT (sem validar assinatura, apenas para logging)
            import jwt
            from src.infrastructure.security.jwt_handler import SECRET_KEY

            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            return payload.get("sub")  # sub é geralmente o user_id

        except Exception:
            # Se falhar em qualquer ponto, apenas retorna None
            # Não queremos quebrar a aplicação por causa do logging
            return None
