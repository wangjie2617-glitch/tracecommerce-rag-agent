"""Administrator user lifecycle operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.repositories.users import UserRepository
from app.schemas.auth import UserData
from app.schemas.users import AdminUserCreate, AdminUserUpdate
from app.services.auth import _to_user_data


class UserAdminService:
    """Create, list, and update users through explicit administrator actions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def list_users(self) -> list[UserData]:
        return [_to_user_data(user) for user in await self.users.list_users()]

    async def create_user(self, payload: AdminUserCreate) -> UserData:
        if await self.users.get_by_email(str(payload.email)):
            raise ConflictError("该邮箱已经注册")
        role = await self.users.get_or_create_role(payload.role)
        user = await self.users.create(
            email=str(payload.email),
            password_hash=hash_password(payload.password),
            display_name=" ".join(payload.display_name.split()),
            role=role,
        )
        await self.session.commit()
        return _to_user_data(user)

    async def update_user(
        self,
        user_id: UUID,
        payload: AdminUserUpdate,
        *,
        actor_id: UUID,
    ) -> UserData:
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("用户不存在")
        updates = payload.model_dump(exclude_unset=True)
        if updates.get("is_active") is False and user.id == actor_id:
            raise ConflictError("管理员不能停用自己的当前账号")
        if display_name := updates.get("display_name"):
            user.display_name = " ".join(display_name.split())
        if password := updates.get("password"):
            user.password_hash = hash_password(password)
        if role_name := updates.get("role"):
            user.roles = [await self.users.get_or_create_role(role_name)]
        if "is_active" in updates:
            user.is_active = bool(updates["is_active"])
        await self.session.commit()
        return _to_user_data(user)
