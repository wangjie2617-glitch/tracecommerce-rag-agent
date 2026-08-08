"""User and role database operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Role, User


class UserRepository:
    """Persist and query users without exposing SQL to services."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def list_users(self) -> list[User]:
        result = await self.session.execute(select(User).order_by(User.created_at.desc()))
        return list(result.scalars().all())

    async def get_or_create_role(self, name: str, description: str | None = None) -> Role:
        result = await self.session.execute(select(Role).where(Role.name == name))
        role = result.scalar_one_or_none()
        if role is None:
            role = Role(name=name, description=description)
            self.session.add(role)
            await self.session.flush()
        return role

    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        display_name: str,
        role: Role,
    ) -> User:
        user = User(
            email=email.lower(),
            password_hash=password_hash,
            display_name=display_name,
            roles=[role],
        )
        self.session.add(user)
        await self.session.flush()
        return user
