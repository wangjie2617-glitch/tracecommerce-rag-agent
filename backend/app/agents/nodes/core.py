"""Traceable LangGraph node implementations."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from app.agents.state import AgentState
from app.core.logging import get_logger
from app.rag.citation import build_citations, verify_citations
from app.rag.evaluator import EvidenceEvaluator, classify_evidence_level
from app.rag.llm import LLMProvider, detect_language_locally
from app.rag.reranker import Reranker
from app.rag.retriever import HybridRetriever
from app.rag.types import RetrievedDocument

logger = get_logger(__name__)
FALLBACK_ANSWER = "当前知识库中没有足够的信息支持该结论。"


class AgentNodes:
    """All Agent operations with consistent node-level tracing."""

    PROMPT_INJECTION_MARKERS = (
        "ignore previous",
        "ignore all instructions",
        "system prompt",
        "忽略之前",
        "忽略以上",
        "系统提示词",
    )
    HIGH_RISK_MARKERS = (
        "legal advice",
        "lawsuit",
        "guaranteed tax",
        "法律意见",
        "起诉",
        "保证税率",
        "人身伤害",
    )

    def __init__(
        self,
        *,
        llm: LLMProvider,
        retriever: HybridRetriever,
        reranker: Reranker,
        evaluator: EvidenceEvaluator,
        retrieval_top_k: int,
        rerank_top_k: int,
    ) -> None:
        self.llm = llm
        self.retriever = retriever
        self.reranker = reranker
        self.evaluator = evaluator
        self.retrieval_top_k = retrieval_top_k
        self.rerank_top_k = rerank_top_k

    async def _run(
        self,
        name: str,
        state: AgentState,
        operation: Callable[[], Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        started_at = datetime.now(UTC)
        started = time.perf_counter()
        status = "success"
        error: str | None = None
        try:
            updates = await operation()
        except Exception as exc:
            status = "error"
            error = str(exc)
            updates = {"error": error}
            logger.exception(
                "agent_node_failed",
                extra={"agent_node": name, "error_code": "agent_node_failed"},
            )
        ended_at = datetime.now(UTC)
        trace = {
            "node": name,
            "status": status,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "input_summary": self._input_summary(state),
            "output_summary": self._output_summary(updates),
            "error": error,
        }
        logger.info(
            "agent_node",
            extra={
                "agent_node": name,
                "status": status,
                "duration_ms": trace["duration_ms"],
            },
        )
        updates["execution_trace"] = [*state.get("execution_trace", []), trace]
        return updates

    @staticmethod
    def _input_summary(state: AgentState) -> str:
        query = state.get("rewritten_query") or state.get("original_query") or ""
        return f"query={query[:160]!r}; retry={state.get('retry_count', 0)}"

    @staticmethod
    def _output_summary(updates: dict[str, Any]) -> str:
        safe = {
            key: value
            for key, value in updates.items()
            if key not in {"retrieved_documents", "reranked_documents", "answer", "citations"}
        }
        if "retrieved_documents" in updates:
            safe["retrieved_count"] = len(updates["retrieved_documents"])
        if "reranked_documents" in updates:
            safe["reranked_count"] = len(updates["reranked_documents"])
        return str(safe)[:500]

    async def validate_input(self, state: AgentState) -> dict[str, Any]:
        async def operation() -> dict[str, Any]:
            query = " ".join(state.get("original_query", "").split())
            if not query:
                return {"error": "问题不能为空"}
            if len(query) > 2000:
                return {"error": "问题长度不能超过 2000 字符"}
            lowered = query.lower()
            risk_flags = list(state.get("risk_flags", []))
            warnings = list(state.get("warnings", []))
            if any(marker in lowered for marker in self.PROMPT_INJECTION_MARKERS):
                risk_flags.append("prompt_injection_attempt")
                warnings.append("检测到可能的 Prompt Injection，系统将仅使用知识库资料回答")
            return {"original_query": query, "risk_flags": risk_flags, "warnings": warnings}

        return await self._run("validate_input", state, operation)

    async def detect_language(self, state: AgentState) -> dict[str, Any]:
        async def operation() -> dict[str, Any]:
            return {"language": detect_language_locally(state["original_query"])}

        return await self._run("detect_language", state, operation)

    async def classify_intent(self, state: AgentState) -> dict[str, Any]:
        async def operation() -> dict[str, Any]:
            intent, region = await self.llm.classify_intent(state["original_query"])
            return {"intent": intent, "region": region}

        return await self._run("classify_intent", state, operation)

    async def rewrite_query(self, state: AgentState) -> dict[str, Any]:
        async def operation() -> dict[str, Any]:
            rewritten = await self.llm.rewrite_query(
                state["original_query"],
                language=state["language"],
                retry_count=state.get("retry_count", 0),
            )
            return {"rewritten_query": rewritten}

        return await self._run("rewrite_query", state, operation)

    async def build_filters(self, state: AgentState) -> dict[str, Any]:
        async def operation() -> dict[str, Any]:
            supplied = state.get("filters", {})
            allowed = {
                key: value
                for key, value in supplied.items()
                if key
                in {
                    "company_name",
                    "language",
                    "country_or_region",
                    "business_category",
                    "source_type",
                    "is_active",
                    "version",
                }
                and value is not None
            }
            allowed.setdefault("company_name", "Shopify")
            allowed["is_active"] = True
            if state.get("language") == "zh-CN":
                allowed.setdefault("language", "zh-CN")
            if state.get("region") and "country_or_region" not in allowed:
                allowed["country_or_region"] = state["region"]
            return {"filters": allowed}

        return await self._run("build_filters", state, operation)

    async def retrieve_documents(self, state: AgentState) -> dict[str, Any]:
        async def operation() -> dict[str, Any]:
            documents = await self.retriever.retrieve(
                state["rewritten_query"],
                filters=state.get("filters", {}),
                top_k=self.retrieval_top_k,
            )
            updates: dict[str, Any] = {
                "retrieved_documents": [item.model_dump(mode="json") for item in documents]
            }
            if not documents:
                updates["retry_count"] = state.get("retry_count", 0) + 1
            return updates

        return await self._run("retrieve_documents", state, operation)

    async def rerank_documents(self, state: AgentState) -> dict[str, Any]:
        async def operation() -> dict[str, Any]:
            documents = [
                RetrievedDocument.model_validate(item)
                for item in state.get("retrieved_documents", [])
            ]
            reranked = await self.reranker.rerank(
                state["rewritten_query"],
                documents,
                top_k=self.rerank_top_k,
            )
            return {"reranked_documents": [item.model_dump(mode="json") for item in reranked]}

        return await self._run("rerank_documents", state, operation)

    async def evaluate_evidence(self, state: AgentState) -> dict[str, Any]:
        async def operation() -> dict[str, Any]:
            documents = [
                RetrievedDocument.model_validate(item)
                for item in state.get("reranked_documents", [])
            ]
            score, sufficient = self.evaluator.evaluate(documents)
            updates: dict[str, Any] = {
                "evidence_score": score,
                "evidence_sufficient": sufficient,
            }
            if not sufficient:
                updates["retry_count"] = state.get("retry_count", 0) + 1
            return updates

        return await self._run("evaluate_evidence", state, operation)

    async def generate_answer(self, state: AgentState) -> dict[str, Any]:
        async def operation() -> dict[str, Any]:
            documents = [
                RetrievedDocument.model_validate(item)
                for item in state.get("reranked_documents", [])
            ]
            answer = await self.llm.generate_answer(
                state["original_query"],
                documents,
                language=state["language"],
            )
            citations = build_citations(documents)
            return {"answer": answer, "citations": citations}

        return await self._run("generate_answer", state, operation)

    async def verify_citations(self, state: AgentState) -> dict[str, Any]:
        async def operation() -> dict[str, Any]:
            documents = [
                RetrievedDocument.model_validate(item)
                for item in state.get("reranked_documents", [])
            ]
            grounded = verify_citations(state.get("citations", []), documents)
            return {"grounded": grounded}

        return await self._run("verify_citations", state, operation)

    async def risk_check(self, state: AgentState) -> dict[str, Any]:
        async def operation() -> dict[str, Any]:
            lowered = state["original_query"].lower()
            flags = list(state.get("risk_flags", []))
            warnings = list(state.get("warnings", []))
            if any(marker in lowered for marker in self.HIGH_RISK_MARKERS):
                flags.append("high_risk_advice")
                warnings.append("该问题可能涉及法律、税务或人身风险，请由专业人员复核")
            return {"risk_flags": sorted(set(flags)), "warnings": sorted(set(warnings))}

        return await self._run("risk_check", state, operation)

    async def finalize_response(self, state: AgentState) -> dict[str, Any]:
        async def operation() -> dict[str, Any]:
            evidence_score = min(max(float(state.get("evidence_score", 0.0)), 0.0), 1.0)
            confidence = evidence_score
            if state.get("risk_flags"):
                confidence = min(confidence, 0.75)
            grounded = bool(state.get("grounded")) and state.get("answer") != FALLBACK_ANSWER
            return {
                "evidence_score": round(evidence_score, 4),
                "evidence_level": classify_evidence_level(evidence_score, grounded),
                # Kept for API compatibility. It is deprecated in favor of evidence_score.
                "confidence": round(confidence, 4),
                "grounded": grounded,
            }

        return await self._run("finalize_response", state, operation)

    async def fallback_response(self, state: AgentState) -> dict[str, Any]:
        async def operation() -> dict[str, Any]:
            warnings = list(state.get("warnings", []))
            reason = state.get("error") or "检索证据不足或引用无法支持答案"
            warnings.append(reason)
            return {
                "answer": FALLBACK_ANSWER,
                "citations": [],
                "evidence_score": 0.0,
                "evidence_level": "insufficient",
                "confidence": 0.0,
                "grounded": False,
                "warnings": sorted(set(warnings)),
            }

        return await self._run("fallback_response", state, operation)
