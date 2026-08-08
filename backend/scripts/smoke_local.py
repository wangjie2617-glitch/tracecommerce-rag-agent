"""Exercise the real local PostgreSQL + Milvus stack through FastAPI."""

from __future__ import annotations

import asyncio

from httpx import ASGITransport, AsyncClient

from app.agents.nodes.core import FALLBACK_ANSWER
from app.config import get_settings
from app.main import app


async def main() -> None:
    settings = get_settings()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://local-smoke",
    ) as client:
        health = await client.get("/health")
        health.raise_for_status()
        ready = await client.get("/ready")
        ready.raise_for_status()
        assert ready.json()["data"]["status"] == "ready", ready.text

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": settings.admin_email, "password": settings.admin_password},
        )
        login.raise_for_status()
        token = login.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        answer = await client.post(
            "/api/v1/chat/query",
            headers=headers,
            json={"query": "Shopify 跨境订单为什么需要填写 HS 编码？"},
        )
        answer.raise_for_status()
        answer_data = answer.json()["data"]
        assert answer_data["grounded"] is True, answer.text
        assert answer_data["evidence_score"] >= 0.0, answer.text
        assert answer_data["evidence_level"] in {"low", "medium", "high"}, answer.text
        assert answer_data["citations"], answer.text
        assert answer_data["language"] == "zh-CN", answer.text
        assert all(
            "/zh-CN/" in citation["source_url"] for citation in answer_data["citations"]
        ), answer.text

        trace = await client.get(
            f"/api/v1/traces/{answer_data['request_id']}",
            headers=headers,
        )
        trace.raise_for_status()
        assert trace.json()["data"]["result"]["citations"], trace.text

        tracking = await client.post(
            "/api/v1/chat/query",
            headers=headers,
            json={"query": "为什么我的商品没有任何的运输记录？"},
        )
        tracking.raise_for_status()
        tracking_data = tracking.json()["data"]
        assert tracking_data["grounded"] is True, tracking.text
        assert tracking_data["evidence_score"] >= settings.min_evidence_score, tracking.text
        assert any(
            citation["source_url"].endswith("/order-tracking")
            for citation in tracking_data["citations"]
        ), tracking.text

        fallback = await client.post(
            "/api/v1/chat/query",
            headers=headers,
            json={"query": "请写一首关于春天的诗"},
        )
        fallback.raise_for_status()
        fallback_data = fallback.json()["data"]
        assert fallback_data["answer"] == FALLBACK_ANSWER, fallback.text
        assert fallback_data["grounded"] is False, fallback.text
        assert fallback_data["evidence_score"] == 0.0, fallback.text
        assert fallback_data["evidence_level"] == "insufficient", fallback.text

        print(
            "本地端到端验证通过: "
            f"ready={ready.json()['data']['status']}, "
            f"grounded_citations={len(answer_data['citations'])}, "
            f"tracking_evidence={tracking_data['evidence_score']}, "
            "fallback=ok"
        )


if __name__ == "__main__":
    asyncio.run(main())
