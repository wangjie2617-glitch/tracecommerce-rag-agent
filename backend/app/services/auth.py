"""Authentication business operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.repositories.users import UserRepository
from app.schemas.auth import RegisterRequest, TokenData, UserData


def _to_user_data(user: User) -> UserData:
    return UserData(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        roles=sorted(role.name for role in user.roles),
        is_active=user.is_active,
    )


class AuthService:
    """Register users, validate credentials, and issue access tokens."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def register(self, payload: RegisterRequest) -> UserData:
        if await self.users.get_by_email(str(payload.email)):
            raise ConflictError("该邮箱已经注册")
        role = await self.users.get_or_create_role(payload.role)
        user = await self.users.create(
            email=str(payload.email),
            password_hash=hash_password(payload.password),
            display_name=payload.display_name,
            role=role,
        )
        await self.session.commit()
        return _to_user_data(user)

    async def login(self, email: str, password: str) -> TokenData:
        user = await self.users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError("邮箱或密码错误")
        if not user.is_active:
            raise AuthenticationError("用户已被停用")
        user_data = _to_user_data(user)
        token, expires_in = create_access_token(user.id, user_data.roles)
        return TokenData(access_token=token, expires_in=expires_in, user=user_data)

    async def get_user(self, user_id: UUID) -> User:
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("用户不存在")
        return user

