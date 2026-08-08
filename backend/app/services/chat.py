"""Chat orchestration through LangGraph and trace persistence."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.logging import thread_id_context
from app.db.models import User
from app.rag.evaluator import classify_evidence_level
from app.repositories.chat import ChatRepository
from app.schemas.chat import (
    ChatAnswerData,
    CitationData,
    ConversationDetail,
    ConversationSummary,
    FeedbackData,
    MessageData,
    RequestTraceData,
    TraceStepData,
)


class ChatService:
    """Run the Agent and persist every evidence and trace record."""

    def __init__(self, session: AsyncSession, graph) -> None:
        self.session = session
        self.graph = graph
        self.repository = ChatRepository(session)

    async def query(
        self,
        *,
        user: User,
        query: str,
        request_id: UUID,
        thread_id: UUID | None,
        filters: dict,
    ) -> ChatAnswerData:
        actual_thread_id = thread_id or uuid4()
        if thread_id is not None:
            conversation = await self.repository.get_conversation(thread_id, user.id)
            if conversation is None:
                raise NotFoundError("会话不存在或不属于当前用户")
        roles = sorted(role.name for role in user.roles)
        initial_state = {
            "request_id": str(request_id),
            "thread_id": str(actual_thread_id),
            "user_id": str(user.id),
            "role": roles[0] if roles else "customer_service",
            "original_query": query,
            "rewritten_query": "",
            "language": "",
            "intent": "",
            "region": None,
            "filters": filters,
            "retrieved_documents": [],
            "reranked_documents": [],
            "evidence_score": 0.0,
            "evidence_level": "insufficient",
            "evidence_sufficient": False,
            "answer": "",
            "citations": [],
            "confidence": 0.0,
            "grounded": False,
            "risk_flags": [],
            "execution_trace": [],
            "warnings": [],
            "retry_count": 0,
            "error": None,
        }
        token = thread_id_context.set(str(actual_thread_id))
        try:
            state = await self.graph.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": str(actual_thread_id)}},
            )
        finally:
            thread_id_context.reset(token)
        await self.repository.persist_interaction(
            user_id=user.id,
            request_id=request_id,
            thread_id=actual_thread_id,
            query=query,
            state=state,
        )
        return self._answer_from_state(request_id, actual_thread_id, state)

    @staticmethod
    def _answer_from_state(request_id: UUID, thread_id: UUID, state: dict) -> ChatAnswerData:
        evidence_score = float(state.get("evidence_score", state.get("confidence", 0.0)))
        grounded = bool(state.get("grounded", False))
        return ChatAnswerData(
            request_id=request_id,
            thread_id=thread_id,
            answer=state["answer"],
            evidence_score=evidence_score,
            evidence_level=state.get("evidence_level")
            or classify_evidence_level(evidence_score, grounded),
            confidence=state.get("confidence", 0.0),
            grounded=grounded,
            intent=state.get("intent") or "out_of_scope",
            language=state.get("language") or "unknown",
            citations=[CitationData.model_validate(item) for item in state.get("citations", [])],
            trace=[TraceStepData.model_validate(item) for item in state.get("execution_trace", [])],
            warnings=state.get("warnings", []),
        )

    async def list_conversations(self, user: User) -> list[ConversationSummary]:
        conversations = await self.repository.list_conversations(user.id)
        return [
            ConversationSummary(
                thread_id=item.thread_id,
                title=item.title,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in conversations
        ]

    async def conversation_detail(self, user: User, thread_id: UUID) -> ConversationDetail:
        conversation = await self.repository.get_conversation(thread_id, user.id)
        if conversation is None:
            raise NotFoundError("会话不存在")
        messages = await self.repository.list_messages(conversation.id)
        return ConversationDetail(
            thread_id=conversation.thread_id,
            title=conversation.title,
            messages=[
                MessageData(
                    id=item.id,
                    role=item.role,
                    content=item.content,
                    request_id=item.request_id,
                    created_at=item.created_at,
                )
                for item in messages
            ],
        )

    async def feedback(
        self,
        user: User,
        *,
        request_id: UUID,
        helpful: bool,
        comment: str | None,
    ) -> FeedbackData:
        rag_request = await self.repository.get_rag_request(request_id)
        if rag_request is None:
            raise NotFoundError("问答请求不存在")
        if rag_request.user_id != user.id and "admin" not in {role.name for role in user.roles}:
            raise AuthorizationError()
        feedback = await self.repository.add_feedback(
            rag_request=rag_request,
            user_id=user.id,
            helpful=helpful,
            comment=comment,
        )
        return FeedbackData(id=feedback.id, request_id=request_id, helpful=helpful)

    async def trace(self, user: User, request_id: UUID) -> RequestTraceData:
        rag_request = await self.repository.get_rag_request(request_id)
        if rag_request is None:
            raise NotFoundError("追踪记录不存在")
        if rag_request.user_id != user.id and "admin" not in {role.name for role in user.roles}:
            raise AuthorizationError()
        traces, citations, retrieval = await self.repository.trace_rows(rag_request.id)
        evidence_score = float(rag_request.evidence_score)
        answer = ChatAnswerData(
            request_id=rag_request.request_id,
            thread_id=rag_request.thread_id,
            answer=rag_request.answer,
            evidence_score=evidence_score,
            evidence_level=rag_request.evidence_level
            or classify_evidence_level(evidence_score, rag_request.grounded),
            confidence=rag_request.confidence,
            grounded=rag_request.grounded,
            intent=rag_request.intent,
            language=rag_request.language,
            citations=[
                CitationData(
                    document_id=item.document_id,
                    chunk_id=item.chunk_id,
                    title=item.title,
                    section_title=item.section_title,
                    source_url=item.source_url,
                    quoted_text=item.quoted_text,
                    retrieval_score=item.retrieval_score,
                    rerank_score=item.rerank_score,
                    crawled_at=item.crawled_at,
                )
                for item in citations
            ],
            trace=[
                TraceStepData(
                    node=item.node,
                    status=item.status,
                    duration_ms=item.duration_ms,
                    started_at=item.started_at,
                    ended_at=item.ended_at,
                    input_summary=item.input_summary,
                    output_summary=item.output_summary,
                    error=item.error,
                )
                for item in traces
            ],
            warnings=rag_request.warnings,
        )
        retrieved = [
            {
                "document_id": str(item.document_id),
                "chunk_id": str(item.chunk_id),
                "rank": item.rank,
                "retrieval_score": item.retrieval_score,
                "rerank_score": item.rerank_score,
                **item.metadata_json,
            }
            for item in retrieval
        ]
        return RequestTraceData(result=answer, retrieved=retrieved)
