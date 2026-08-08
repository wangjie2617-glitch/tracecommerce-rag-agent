"""Seed roles and one administrator account."""

from __future__ import annotations

import asyncio

from app.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionFactory
from app.repositories.users import UserRepository


async def main() -> None:
    settings = get_settings()
    async with SessionFactory() as session:
        users = UserRepository(session)
        role_descriptions = {
            "admin": "系统管理员",
            "customer_service": "跨境电商客服",
            "operator": "跨境电商运营",
        }
        roles = {
            name: await users.get_or_create_role(name, description)
            for name, description in role_descriptions.items()
        }
        existing = await users.get_by_email(settings.admin_email)
        if existing is None:
            await users.create(
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                display_name="TraceCommerce Admin",
                role=roles["admin"],
            )
        await session.commit()
        print(f"管理员已就绪: {settings.admin_email}")


if __name__ == "__main__":
    asyncio.run(main())
