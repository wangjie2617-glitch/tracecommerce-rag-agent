"""End-to-end HTTP tests for chat persistence, trace lookup, and feedback."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.nodes.core import FALLBACK_ANSWER
from app.core.security import create_access_token, hash_password
from app.db.models import Role, User
from app.db.session import get_session
from app.dependencies import get_agent_graph
from app.main import app


class FallbackGraph:
    async def ainvoke(self, state: dict, config: dict) -> dict:
        del config
        return {
            **state,
            "answer": FALLBACK_ANSWER,
            "intent": "policy_question",
            "language": "zh",
            "confidence": 0.0,
            "grounded": False,
            "warnings": ["insufficient_evidence"],
            "retrieved_documents": [],
            "reranked_documents": [],
            "citations": [],
            "execution_trace": [],
        }


@pytest.mark.asyncio
async def test_chat_query_can_be_traced_and_rated(session: AsyncSession) -> None:
    role = Role(name="operator")
    user = User(
        email="chat-api@example.com",
        password_hash=hash_password("SecurePass123!"),
        display_name="Chat Operator",
        roles=[role],
    )
    session.add(user)
    await session.commit()
    token, _ = create_access_token(user.id, ["operator"])

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_agent_graph] = lambda: FallbackGraph()
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            answer = await client.post(
                "/api/v1/chat/query",
                headers=headers,
                json={"query": "Shopify 的跨境退货规则是什么？"},
            )
            assert answer.status_code == 200
            payload = answer.json()["data"]
            assert payload["answer"] == FALLBACK_ANSWER
            assert payload["grounded"] is False
            assert payload["evidence_score"] == 0.0
            assert payload["evidence_level"] == "insufficient"

            trace = await client.get(
                f"/api/v1/traces/{payload['request_id']}",
                headers=headers,
            )
            assert trace.status_code == 200
            trace_result = trace.json()["data"]["result"]
            assert trace_result["request_id"] == payload["request_id"]
            assert trace_result["evidence_score"] == 0.0
            assert trace_result["evidence_level"] == "insufficient"

            conversations = await client.get("/api/v1/chat/conversations", headers=headers)
            assert conversations.status_code == 200
            assert conversations.json()["data"][0]["thread_id"] == payload["thread_id"]

            feedback = await client.post(
                "/api/v1/chat/feedback",
                headers=headers,
                json={
                    "request_id": payload["request_id"],
                    "helpful": False,
                    "comment": "知识库证据不足时正确拒答。",
                },
            )
            assert feedback.status_code == 200
            assert feedback.json()["data"]["helpful"] is False
    finally:
        app.dependency_overrides.clear()
