"""Administrator user-management API integration tests."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.db.models import Role, User
from app.db.session import get_session
from app.main import app


@pytest.mark.asyncio
async def test_admin_can_create_list_and_disable_user(session: AsyncSession) -> None:
    admin_role = Role(name="admin")
    admin = User(
        email="admin-api@example.com",
        password_hash=hash_password("AdminPass123!"),
        display_name="API Admin",
        roles=[admin_role],
    )
    session.add(admin)
    await session.commit()
    token, _ = create_access_token(admin.id, ["admin"])

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = override_session
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/api/v1/users",
                headers=headers,
                json={
                    "email": "service-api@example.com",
                    "password": "SecurePass123!",
                    "display_name": "Service Agent",
                    "role": "customer_service",
                },
            )
            assert created.status_code == 201
            user_id = created.json()["data"]["id"]

            listed = await client.get("/api/v1/users", headers=headers)
            assert listed.status_code == 200
            assert {item["email"] for item in listed.json()["data"]} == {
                "admin-api@example.com",
                "service-api@example.com",
            }

            disabled = await client.patch(
                f"/api/v1/users/{user_id}",
                headers=headers,
                json={"is_active": False},
            )
            assert disabled.status_code == 200
            assert disabled.json()["data"]["is_active"] is False
    finally:
        app.dependency_overrides.clear()
