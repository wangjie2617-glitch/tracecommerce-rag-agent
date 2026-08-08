"""Traceable chat, conversation history, and feedback endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.session import get_session
from app.dependencies import get_agent_graph, require_roles
from app.schemas.chat import (
    ChatAnswerData,
    ChatQueryRequest,
    ConversationDetail,
    ConversationSummary,
    FeedbackData,
    FeedbackRequest,
)
from app.schemas.common import ApiResponse
from app.services.chat import ChatService

router = APIRouter()
ChatUser = Annotated[User, Depends(require_roles("admin", "customer_service", "operator"))]


@router.post("/query", response_model=ApiResponse[ChatAnswerData])
async def query(
    payload: ChatQueryRequest,
    request: Request,
    user: ChatUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    graph: Annotated[object, Depends(get_agent_graph)],
) -> ApiResponse[ChatAnswerData]:
    data = await ChatService(session, graph).query(
        user=user,
        query=payload.query,
        request_id=UUID(request.state.request_id),
        thread_id=payload.thread_id,
        filters=payload.filters,
    )
    return ApiResponse(request_id=request.state.request_id, data=data)


@router.get("/conversations", response_model=ApiResponse[list[ConversationSummary]])
async def conversations(
    request: Request,
    user: ChatUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[list[ConversationSummary]]:
    data = await ChatService(session, None).list_conversations(user)
    return ApiResponse(request_id=request.state.request_id, data=data)


@router.get("/conversations/{thread_id}", response_model=ApiResponse[ConversationDetail])
async def conversation_detail(
    thread_id: UUID,
    request: Request,
    user: ChatUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[ConversationDetail]:
    data = await ChatService(session, None).conversation_detail(user, thread_id)
    return ApiResponse(request_id=request.state.request_id, data=data)


@router.post("/feedback", response_model=ApiResponse[FeedbackData])
async def feedback(
    payload: FeedbackRequest,
    request: Request,
    user: ChatUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[FeedbackData]:
    data = await ChatService(session, None).feedback(
        user,
        request_id=payload.request_id,
        helpful=payload.helpful,
        comment=payload.comment,
    )
    return ApiResponse(request_id=request.state.request_id, data=data)
