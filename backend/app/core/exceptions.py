"""Domain exceptions and unified API exception handlers."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger, request_id_context

logger = get_logger(__name__)


class AppError(Exception):
    """Base exception with an HTTP status and stable application code."""

    def __init__(self, message: str, *, code: str = "application_error", status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class AuthenticationError(AppError):
    def __init__(self, message: str = "身份认证失败") -> None:
        super().__init__(message, code="authentication_failed", status_code=401)


class AuthorizationError(AppError):
    def __init__(self, message: str = "没有执行该操作的权限") -> None:
        super().__init__(message, code="permission_denied", status_code=403)


class NotFoundError(AppError):
    def __init__(self, message: str = "资源不存在") -> None:
        super().__init__(message, code="not_found", status_code=404)


class ConflictError(AppError):
    def __init__(self, message: str = "资源已存在") -> None:
        super().__init__(message, code="conflict", status_code=409)


class DependencyUnavailableError(AppError):
    def __init__(self, message: str, *, code: str = "dependency_unavailable") -> None:
        super().__init__(message, code=code, status_code=503)


def install_exception_handlers(app: FastAPI) -> None:
    """Register consistent JSON error responses."""

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        logger.warning("application_error", extra={"error_code": exc.code})
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "request_id": request_id_context.get(),
                "error": {"code": exc.code, "message": exc.message},
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "request_id": request_id_context.get(),
                "error": {
                    "code": "validation_error",
                    "message": "请求参数校验失败",
                    "details": exc.errors(),
                },
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", extra={"error_code": "internal_error"})
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "request_id": request_id_context.get(),
                "error": {"code": "internal_error", "message": "服务器内部错误"},
            },
        )

