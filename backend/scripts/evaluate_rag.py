"""Evaluate retrieval/reranking and recommend an evidence threshold."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.dependencies import get_embedding_provider, get_reranker, get_vector_store
from app.rag.calibration import CalibrationPoint, choose_threshold
from app.rag.evaluator import EvidenceEvaluator, classify_evidence_level
from app.rag.retriever import HybridRetriever

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = BACKEND_DIR / "data" / "evaluation" / "rag_eval.jsonl"
DEFAULT_OUTPUT = BACKEND_DIR / "reports" / "rag_evaluation.json"


def load_dataset(path: Path) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            sample = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number} 不是合法 JSON") from exc
        required = {"id", "query", "answerable", "gold_urls"}
        missing = required - sample.keys()
        if missing:
            raise ValueError(f"{path}:{line_number} 缺少字段: {sorted(missing)}")
        samples.append(sample)
    if not samples:
        raise ValueError("评测集不能为空")
    return samples


def reciprocal_rank(urls: list[str], gold_urls: set[str]) -> float:
    for rank, url in enumerate(urls, start=1):
        if url in gold_urls:
            return 1.0 / rank
    return 0.0


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    threshold = payload["recommended_threshold"]
    lines = [
        "# RAG 检索与证据阈值评测",
        "",
        f"- Embedding：`{payload['runtime']['embedding_provider']}` / "
        f"`{payload['runtime']['embedding_model']}`",
        f"- Reranker：`{payload['runtime']['reranker_provider']}` / "
        f"`{payload['runtime']['reranker_model']}`",
        f"- Collection：`{payload['runtime']['collection']}`",
        f"- 样本数：{summary['samples']}",
        f"- Answerable Hit@K：{summary['answerable_hit_at_k']:.4f}",
        f"- Answerable MRR：{summary['answerable_mrr']:.4f}",
        f"- 当前阈值误放行无答案数：{summary['unanswerable_false_accepts']}",
        "",
        "## 推荐阈值",
        "",
        f"- threshold：`{threshold['threshold']}`",
        f"- precision：`{threshold['precision']}`",
        f"- recall：`{threshold['recall']}`",
        f"- F1：`{threshold['f1']}`",
        "",
        "> 该阈值只对当前模型、Collection 和评测集有效；更换模型或知识库后必须重跑。",
        "",
        "## 明细",
        "",
        "| ID | Query | Gold Hit | Evidence | Level | Sufficient |",
        "|---|---|---:|---:|---|---:|",
    ]
    for item in payload["items"]:
        query = str(item["query"]).replace("|", "\\|")
        lines.append(
            f"| {item['id']} | {query} | {item['gold_hit']} | "
            f"{item['evidence_score']:.4f} | {item['evidence_level']} | "
            f"{item['evidence_sufficient']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def evaluate(dataset_path: Path, output_path: Path, minimum_precision: float) -> None:
    settings = get_settings()
    samples = load_dataset(dataset_path)
    embedding = get_embedding_provider()
    vector_store = get_vector_store()
    reranker = get_reranker()
    retriever = HybridRetriever(
        embedding,
        vector_store,
        minimum_score=settings.min_retrieval_score,
    )
    evaluator = EvidenceEvaluator(settings.min_evidence_score)
    items: list[dict[str, Any]] = []
    points: list[CalibrationPoint] = []

    for sample in samples:
        filters = {"language": "zh-CN", **sample.get("filters", {})}
        documents = await retriever.retrieve(
            sample["query"],
            filters=filters,
            top_k=settings.retrieval_top_k,
        )
        reranked = await reranker.rerank(
            sample["query"],
            documents,
            top_k=settings.rerank_top_k,
        )
        score, sufficient = evaluator.evaluate(reranked)
        returned_urls = [document.source_url for document in reranked]
        gold_urls = set(sample["gold_urls"])
        rank_value = reciprocal_rank(returned_urls, gold_urls)
        gold_hit = rank_value > 0
        should_answer = bool(sample["answerable"]) and gold_hit
        points.append(CalibrationPoint(score=score, positive=should_answer))
        items.append(
            {
                "id": sample["id"],
                "query": sample["query"],
                "answerable": bool(sample["answerable"]),
                "gold_hit": gold_hit,
                "reciprocal_rank": round(rank_value, 4),
                "evidence_score": score,
                "evidence_level": classify_evidence_level(score, sufficient),
                "evidence_sufficient": sufficient,
                "returned_urls": returned_urls,
                "top_retrieval_score": max(
                    (document.retrieval_score for document in documents),
                    default=0.0,
                ),
                "top_rerank_score": max(
                    (
                        document.rerank_score
                        for document in reranked
                        if document.rerank_score is not None
                    ),
                    default=0.0,
                ),
            }
        )

    answerable_items = [item for item in items if item["answerable"]]
    hit_count = sum(item["gold_hit"] for item in answerable_items)
    mrr = (
        sum(item["reciprocal_rank"] for item in answerable_items) / len(answerable_items)
        if answerable_items
        else 0.0
    )
    unanswerable_false_accepts = sum(
        not item["answerable"] and item["evidence_sufficient"] for item in items
    )
    recommended = choose_threshold(points, minimum_precision=minimum_precision)
    payload = {
        "runtime": {
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model,
            "reranker_provider": settings.reranker_provider,
            "reranker_model": settings.reranker_model,
            "collection": settings.milvus_collection,
            "retrieval_top_k": settings.retrieval_top_k,
            "rerank_top_k": settings.rerank_top_k,
            "current_min_retrieval_score": settings.min_retrieval_score,
            "current_min_evidence_score": settings.min_evidence_score,
        },
        "summary": {
            "samples": len(items),
            "answerable_samples": len(answerable_items),
            "answerable_hit_at_k": round(
                hit_count / len(answerable_items) if answerable_items else 0.0,
                4,
            ),
            "answerable_mrr": round(mrr, 4),
            "unanswerable_false_accepts": unanswerable_false_accepts,
        },
        "recommended_threshold": asdict(recommended),
        "items": items,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown(payload, output_path.with_suffix(".md"))
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(
        "推荐 MIN_EVIDENCE_SCORE="
        f"{payload['recommended_threshold']['threshold']} "
        f"(precision={payload['recommended_threshold']['precision']}, "
        f"recall={payload['recommended_threshold']['recall']})"
    )
    print(f"报告: {output_path}")
    print(f"报告: {output_path.with_suffix('.md')}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--minimum-precision", type=float, default=0.95)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(evaluate(args.dataset, args.output, args.minimum_precision))
