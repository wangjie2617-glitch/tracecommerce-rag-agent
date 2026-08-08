"""Top-level API router."""

from fastapi import APIRouter

from app.api.v1 import auth, chat, documents, knowledge_sources, system, traces, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(knowledge_sources.router, prefix="/knowledge-sources", tags=["Knowledge Base"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(traces.router, prefix="/traces", tags=["Trace"])
api_router.include_router(system.router, prefix="/system", tags=["System"])
