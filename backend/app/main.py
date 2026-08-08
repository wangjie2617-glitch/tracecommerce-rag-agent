"""FastAPI application factory and process entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.core.exceptions import install_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.schemas.common import ApiResponse, HealthData, ReadyData


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize lightweight process resources; heavy models remain lazy."""
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.log_level)
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="面向跨境电商客服与运营的可追溯 RAG Agent 系统",
        lifespan=lifespan,
    )
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_exception_handlers(application)
    application.include_router(api_router, prefix=settings.api_v1_prefix)

    @application.get("/health", response_model=ApiResponse[HealthData], tags=["System"])
    async def health(request: Request) -> ApiResponse[HealthData]:
        return ApiResponse(
            request_id=request.state.request_id,
            data=HealthData(status="ok", service=settings.app_name, environment=settings.app_env),
        )

    @application.get("/ready", response_model=ApiResponse[ReadyData], tags=["System"])
    async def ready(request: Request) -> ApiResponse[ReadyData]:
        from app.dependencies import dependency_health

        state = await dependency_health()
        return ApiResponse(request_id=request.state.request_id, data=ReadyData(**state))

    return application


app = create_app()
