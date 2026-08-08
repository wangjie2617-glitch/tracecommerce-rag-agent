"""Conversation, RAG request, citation, trace, and feedback persistence."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AgentTrace,
    AnswerFeedback,
    Citation,
    Conversation,
    Message,
    RagRequest,
    RetrievalRecord,
)
from app.rag.evaluator import classify_evidence_level


class ChatRepository:
    """Persist a complete traceable RAG interaction."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_conversation(self, thread_id: UUID, user_id: UUID) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.thread_id == thread_id,
                Conversation.user_id == user_id,
                Conversation.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_conversation(
        self,
        *,
        thread_id: UUID,
        user_id: UUID,
        title: str,
    ) -> Conversation:
        conversation = await self.get_conversation(thread_id, user_id)
        if conversation is None:
            conversation = Conversation(thread_id=thread_id, user_id=user_id, title=title[:300])
            self.session.add(conversation)
            await self.session.flush()
        return conversation

    async def list_conversations(self, user_id: UUID) -> list[Conversation]:
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.is_active.is_(True))
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())

    async def list_messages(self, conversation_id: UUID) -> list[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_rag_request(self, request_id: UUID) -> RagRequest | None:
        result = await self.session.execute(
            select(RagRequest).where(RagRequest.request_id == request_id)
        )
        return result.scalar_one_or_none()

    async def persist_interaction(
        self,
        *,
        user_id: UUID,
        request_id: UUID,
        thread_id: UUID,
        query: str,
        state: dict,
    ) -> RagRequest:
        grounded = bool(state.get("grounded", False))
        evidence_score = float(
            state.get("evidence_score", state.get("confidence", 0.0))
        )
        evidence_level = state.get("evidence_level") or classify_evidence_level(
            evidence_score, grounded
        )
        conversation = await self.get_or_create_conversation(
            thread_id=thread_id,
            user_id=user_id,
            title=query,
        )
        self.session.add(
            Message(
                conversation_id=conversation.id,
                request_id=request_id,
                role="user",
                content=query,
            )
        )
        self.session.add(
            Message(
                conversation_id=conversation.id,
                request_id=request_id,
                role="assistant",
                content=state["answer"],
                metadata_json={
                    "grounded": grounded,
                    "evidence_score": evidence_score,
                    "evidence_level": evidence_level,
                    "confidence": state.get("confidence", 0.0),
                    "citations": state.get("citations", []),
                },
            )
        )
        rag_request = RagRequest(
            request_id=request_id,
            thread_id=thread_id,
            user_id=user_id,
            original_query=query,
            rewritten_query=state.get("rewritten_query"),
            answer=state["answer"],
            intent=state.get("intent", "out_of_scope"),
            language=state.get("language", "unknown"),
            region=state.get("region"),
            evidence_score=evidence_score,
            evidence_level=evidence_level,
            confidence=float(state.get("confidence", 0.0)),
            grounded=grounded,
            warnings=state.get("warnings", []),
        )
        self.session.add(rag_request)
        await self.session.flush()

        documents = state.get("reranked_documents") or state.get("retrieved_documents", [])
        for rank, document in enumerate(documents, start=1):
            self.session.add(
                RetrievalRecord(
                    rag_request_id=rag_request.id,
                    document_id=UUID(str(document["document_id"])),
                    chunk_id=UUID(str(document["chunk_id"])),
                    rank=rank,
                    retrieval_score=float(document["retrieval_score"]),
                    rerank_score=document.get("rerank_score"),
                    metadata_json={
                        "title": document["title"],
                        "source_url": document["source_url"],
                        "section_title": document.get("section_title"),
                    },
                )
            )
        for citation in state.get("citations", []):
            self.session.add(
                Citation(
                    rag_request_id=rag_request.id,
                    document_id=UUID(str(citation["document_id"])),
                    chunk_id=UUID(str(citation["chunk_id"])),
                    title=citation["title"],
                    section_title=citation.get("section_title"),
                    source_url=citation["source_url"],
                    quoted_text=citation["quoted_text"],
                    retrieval_score=float(citation["retrieval_score"]),
                    rerank_score=citation.get("rerank_score"),
                    crawled_at=datetime.fromisoformat(str(citation["crawled_at"])),
                )
            )
        for trace in state.get("execution_trace", []):
            self.session.add(
                AgentTrace(
                    rag_request_id=rag_request.id,
                    node=trace["node"],
                    status=trace["status"],
                    duration_ms=float(trace["duration_ms"]),
                    input_summary=trace.get("input_summary"),
                    output_summary=trace.get("output_summary"),
                    error=trace.get("error"),
                    started_at=datetime.fromisoformat(str(trace["started_at"])),
                    ended_at=datetime.fromisoformat(str(trace["ended_at"])),
                )
            )
        await self.session.commit()
        return rag_request

    async def add_feedback(
        self,
        *,
        rag_request: RagRequest,
        user_id: UUID,
        helpful: bool,
        comment: str | None,
    ) -> AnswerFeedback:
        feedback = AnswerFeedback(
            rag_request_id=rag_request.id,
            user_id=user_id,
            helpful=helpful,
            comment=comment,
        )
        self.session.add(feedback)
        await self.session.commit()
        return feedback

    async def trace_rows(self, rag_request_id: UUID):
        traces = await self.session.execute(
            select(AgentTrace)
            .where(AgentTrace.rag_request_id == rag_request_id)
            .order_by(AgentTrace.started_at.asc())
        )
        citations = await self.session.execute(
            select(Citation)
            .where(Citation.rag_request_id == rag_request_id)
            .order_by(Citation.created_at.asc())
        )
        retrieval = await self.session.execute(
            select(RetrievalRecord)
            .where(RetrievalRecord.rag_request_id == rag_request_id)
            .order_by(RetrievalRecord.rank.asc())
        )
        return list(traces.scalars()), list(citations.scalars()), list(retrieval.scalars())
