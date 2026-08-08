"""Authentication API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.session import get_session
from app.dependencies import get_current_user
from app.schemas.auth import LoginRequest, RegisterRequest, TokenData, UserData
from app.schemas.common import ApiResponse
from app.services.auth import AuthService, _to_user_data

router = APIRouter()


@router.post("/register", response_model=ApiResponse[UserData], status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[UserData]:
    """Register a customer-service or operator account."""
    data = await AuthService(session).register(payload)
    return ApiResponse(request_id=request.state.request_id, data=data)


@router.post("/login", response_model=ApiResponse[TokenData])
async def login(
    payload: LoginRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[TokenData]:
    """Validate credentials and return a JWT access token."""
    data = await AuthService(session).login(str(payload.email), payload.password)
    return ApiResponse(request_id=request.state.request_id, data=data)


@router.get("/me", response_model=ApiResponse[UserData])
async def me(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[UserData]:
    """Return the authenticated user's profile and roles."""
    return ApiResponse(request_id=request.state.request_id, data=_to_user_data(user))

