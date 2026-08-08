"""Request context and access logging middleware."""

from __future__ import annotations

import time
from uuid import UUID, uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.logging import get_logger, request_id_context

logger = get_logger(__name__)


def _safe_request_id(value: str | None) -> str:
    if value:
        try:
            return str(UUID(value))
        except ValueError:
            pass
    return str(uuid4())


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a safe request ID and emit one access log per request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = _safe_request_id(request.headers.get("X-Request-ID"))
        token = request_id_context.set(request_id)
        request.state.request_id = request_id
        started = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "http_request",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code if response else 500,
                    "duration_ms": duration_ms,
                },
            )
            request_id_context.reset(token)

