"""Compile the LangGraph workflow with retries and conditional fallbacks."""

from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.nodes.core import AgentNodes
from app.agents.state import AgentState


def _after_validation(state: AgentState) -> str:
    return "fallback_response" if state.get("error") else "detect_language"


def _after_intent(state: AgentState) -> str:
    if state.get("error") or state.get("intent") == "out_of_scope":
        return "fallback_response"
    return "rewrite_query"


def _after_retrieval(state: AgentState) -> str:
    if state.get("error"):
        return "fallback_response"
    if state.get("retrieved_documents"):
        return "rerank_documents"
    return "rewrite_query" if state.get("retry_count", 0) <= 2 else "fallback_response"


def _after_evidence(state: AgentState) -> str:
    if state.get("error"):
        return "fallback_response"
    if state.get("evidence_sufficient"):
        return "generate_answer"
    return "rewrite_query" if state.get("retry_count", 0) <= 2 else "fallback_response"


def _after_citation_verification(state: AgentState) -> str:
    if state.get("error") or not state.get("grounded"):
        return "fallback_response"
    return "risk_check"


def build_agent_graph(nodes: AgentNodes, *, checkpointer=None):
    """Build a real LangGraph with named nodes, branches, retry limits, and memory."""
    builder = StateGraph(AgentState)
    builder.add_node("validate_input", nodes.validate_input)
    builder.add_node("detect_language", nodes.detect_language)
    builder.add_node("classify_intent", nodes.classify_intent)
    builder.add_node("rewrite_query", nodes.rewrite_query)
    builder.add_node("build_filters", nodes.build_filters)
    builder.add_node("retrieve_documents", nodes.retrieve_documents)
    builder.add_node("rerank_documents", nodes.rerank_documents)
    builder.add_node("evaluate_evidence", nodes.evaluate_evidence)
    builder.add_node("generate_answer", nodes.generate_answer)
    builder.add_node("verify_citations", nodes.verify_citations)
    builder.add_node("risk_check", nodes.risk_check)
    builder.add_node("finalize_response", nodes.finalize_response)
    builder.add_node("fallback_response", nodes.fallback_response)

    builder.add_edge(START, "validate_input")
    builder.add_conditional_edges(
        "validate_input",
        _after_validation,
        {"detect_language": "detect_language", "fallback_response": "fallback_response"},
    )
    builder.add_edge("detect_language", "classify_intent")
    builder.add_conditional_edges(
        "classify_intent",
        _after_intent,
        {"rewrite_query": "rewrite_query", "fallback_response": "fallback_response"},
    )
    builder.add_edge("rewrite_query", "build_filters")
    builder.add_edge("build_filters", "retrieve_documents")
    builder.add_conditional_edges(
        "retrieve_documents",
        _after_retrieval,
        {
            "rerank_documents": "rerank_documents",
            "rewrite_query": "rewrite_query",
            "fallback_response": "fallback_response",
        },
    )
    builder.add_edge("rerank_documents", "evaluate_evidence")
    builder.add_conditional_edges(
        "evaluate_evidence",
        _after_evidence,
        {
            "generate_answer": "generate_answer",
            "rewrite_query": "rewrite_query",
            "fallback_response": "fallback_response",
        },
    )
    builder.add_edge("generate_answer", "verify_citations")
    builder.add_conditional_edges(
        "verify_citations",
        _after_citation_verification,
        {"risk_check": "risk_check", "fallback_response": "fallback_response"},
    )
    builder.add_edge("risk_check", "finalize_response")
    builder.add_edge("fallback_response", "finalize_response")
    builder.add_edge("finalize_response", END)
    return builder.compile(checkpointer=checkpointer or InMemorySaver())

