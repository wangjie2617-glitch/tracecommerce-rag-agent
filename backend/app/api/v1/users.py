"""Administrator-only user and role management endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.session import get_session
from app.dependencies import require_roles
from app.schemas.auth import UserData
from app.schemas.common import ApiResponse
from app.schemas.users import AdminUserCreate, AdminUserUpdate
from app.services.users import UserAdminService

router = APIRouter()
AdminUser = Annotated[User, Depends(require_roles("admin"))]


@router.get("", response_model=ApiResponse[list[UserData]])
async def list_users(
    request: Request,
    _: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[list[UserData]]:
    data = await UserAdminService(session).list_users()
    return ApiResponse(request_id=request.state.request_id, data=data)


@router.post("", response_model=ApiResponse[UserData], status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: AdminUserCreate,
    request: Request,
    _: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[UserData]:
    data = await UserAdminService(session).create_user(payload)
    return ApiResponse(request_id=request.state.request_id, data=data)


@router.patch("/{user_id}", response_model=ApiResponse[UserData])
async def update_user(
    user_id: UUID,
    payload: AdminUserUpdate,
    request: Request,
    admin: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[UserData]:
    data = await UserAdminService(session).update_user(
        user_id,
        payload,
        actor_id=admin.id,
    )
    return ApiResponse(request_id=request.state.request_id, data=data)
