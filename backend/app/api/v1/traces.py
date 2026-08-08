"""Request trace and citation inspection endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.session import get_session
from app.dependencies import require_roles
from app.schemas.chat import CitationData, RequestTraceData
from app.schemas.common import ApiResponse
from app.services.chat import ChatService

router = APIRouter()
TraceUser = Annotated[User, Depends(require_roles("admin", "customer_service", "operator"))]


@router.get("/{request_id}", response_model=ApiResponse[RequestTraceData])
async def trace(
    request_id: UUID,
    request: Request,
    user: TraceUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[RequestTraceData]:
    data = await ChatService(session, None).trace(user, request_id)
    return ApiResponse(request_id=request.state.request_id, data=data)


@router.get("/{request_id}/citations", response_model=ApiResponse[list[CitationData]])
async def citations(
    request_id: UUID,
    request: Request,
    user: TraceUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[list[CitationData]]:
    data = await ChatService(session, None).trace(user, request_id)
    return ApiResponse(request_id=request.state.request_id, data=list(data.result.citations))
