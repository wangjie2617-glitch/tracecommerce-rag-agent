"""Registration and login API integration tests."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.main import app


@pytest.mark.asyncio
async def test_register_login_and_me(session: AsyncSession) -> None:
    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            register = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "operator@example.com",
                    "password": "SecurePass123!",
                    "display_name": "Test Operator",
                    "role": "operator",
                },
            )
            assert register.status_code == 201
            login = await client.post(
                "/api/v1/auth/login",
                json={"email": "operator@example.com", "password": "SecurePass123!"},
            )
            assert login.status_code == 200
            token = login.json()["data"]["access_token"]
            me = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert me.status_code == 200
            assert me.json()["data"]["roles"] == ["operator"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_blank_request_returns_unified_422(session: AsyncSession) -> None:
    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={"email": "bad", "password": "x", "display_name": ""},
            )
            assert response.status_code == 422
            assert response.json()["error"]["code"] == "validation_error"
    finally:
        app.dependency_overrides.clear()

