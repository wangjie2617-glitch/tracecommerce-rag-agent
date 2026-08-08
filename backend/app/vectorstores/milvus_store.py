"""Milvus collection management and dense/BM25 hybrid retrieval."""

from __future__ import annotations

import asyncio
import hashlib
import math
from collections import Counter
from datetime import datetime
from uuid import UUID

from app.rag.tokenization import tokenize_for_retrieval
from app.rag.types import ChunkRecord, RetrievedDocument


class MilvusVectorStore:
    """pymilvus adapter with runtime vector dimension and safe filters."""

    FILTER_FIELDS = {
        "company_name",
        "language",
        "country_or_region",
        "business_category",
        "source_type",
        "is_active",
        "version",
    }

    def __init__(self, uri: str, collection_name: str, *, token: str = "") -> None:
        from pymilvus import MilvusClient

        self.client = MilvusClient(uri=uri, token=token or None)
        self.collection_name = collection_name
        self._sparse_mode: str | None = None

    async def health(self) -> bool:
        try:
            await asyncio.to_thread(self.client.list_collections)
            return True
        except Exception:
            return False

    def _detect_sparse_mode(self) -> str:
        indexes = set(self.client.list_indexes(self.collection_name))
        return "bm25" if "sparse_bm25" in indexes else "ip"

    async def ensure_collection(self, dimension: int) -> None:
        await asyncio.to_thread(self._ensure_collection_sync, dimension)

    def _ensure_collection_sync(self, dimension: int) -> None:
        from pymilvus import DataType, Function, FunctionType

        if self.client.has_collection(self.collection_name):
            description = self.client.describe_collection(self.collection_name)
            dense_field = next(
                field for field in description["fields"] if field["name"] == "dense_vector"
            )
            existing_dimension = int(dense_field["params"]["dim"])
            if existing_dimension != dimension:
                raise ValueError(
                    f"Milvus Collection 向量维度为 {existing_dimension}，"
                    f"当前 Embedding 维度为 {dimension}；请使用新的 Collection 名称"
                )
            indexes = set(self.client.list_indexes(self.collection_name))
            if "sparse_bm25" in indexes:
                self._sparse_mode = "bm25"
            else:
                self._sparse_mode = "ip"
                if "sparse_ip" not in indexes:
                    sparse_index = self.client.prepare_index_params()
                    sparse_index.add_index(
                        field_name="sparse_vector",
                        index_name="sparse_ip",
                        index_type="SPARSE_INVERTED_INDEX",
                        metric_type="IP",
                    )
                    self.client.create_index(self.collection_name, sparse_index)
            self.client.load_collection(self.collection_name)
            return
        server_version = self.client.get_server_version().removeprefix("v")
        major_minor = tuple(int(item) for item in server_version.split(".")[:2])
        self._sparse_mode = "bm25" if major_minor >= (2, 5) else "ip"
        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=64)
        schema.add_field("chunk_id", DataType.VARCHAR, max_length=36)
        schema.add_field("document_id", DataType.VARCHAR, max_length=36)
        schema.add_field("source_id", DataType.VARCHAR, max_length=36)
        schema.add_field("company_name", DataType.VARCHAR, max_length=200)
        schema.add_field("source_type", DataType.VARCHAR, max_length=32)
        schema.add_field("title", DataType.VARCHAR, max_length=1000)
        schema.add_field("section_title", DataType.VARCHAR, max_length=1000)
        schema.add_field("source_url", DataType.VARCHAR, max_length=4096)
        schema.add_field(
            "content",
            DataType.VARCHAR,
            max_length=65535,
            enable_analyzer=True,
            analyzer_params={"type": "standard"},
        )
        schema.add_field("language", DataType.VARCHAR, max_length=32)
        schema.add_field("country_or_region", DataType.VARCHAR, max_length=100)
        schema.add_field("business_category", DataType.VARCHAR, max_length=100)
        schema.add_field("version", DataType.INT64)
        schema.add_field("is_active", DataType.BOOL)
        schema.add_field("crawled_at", DataType.VARCHAR, max_length=64)
        schema.add_field("dense_vector", DataType.FLOAT_VECTOR, dim=dimension)
        schema.add_field("sparse_vector", DataType.SPARSE_FLOAT_VECTOR)
        if self._sparse_mode == "bm25":
            schema.add_function(
                Function(
                    name="content_bm25",
                    function_type=FunctionType.BM25,
                    input_field_names=["content"],
                    output_field_names=["sparse_vector"],
                )
            )
        indexes = self.client.prepare_index_params()
        indexes.add_index(
            field_name="dense_vector",
            index_name="dense_hnsw",
            index_type="HNSW",
            metric_type="COSINE",
            params={"M": 16, "efConstruction": 200},
        )
        if self._sparse_mode == "bm25":
            indexes.add_index(
                field_name="sparse_vector",
                index_name="sparse_bm25",
                index_type="SPARSE_INVERTED_INDEX",
                metric_type="BM25",
            )
        else:
            indexes.add_index(
                field_name="sparse_vector",
                index_name="sparse_ip",
                index_type="SPARSE_INVERTED_INDEX",
                metric_type="IP",
            )
        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=indexes,
        )

    @staticmethod
    def _hashed_sparse_vector(text: str) -> dict[int, float]:
        """Build a deterministic lexical sparse vector for Milvus 2.4."""
        tokens = tokenize_for_retrieval(text)
        counts: Counter[int] = Counter()
        for token in tokens:
            index = int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:4], "big")
            counts[index] += 1
        weighted = {index: 1.0 + math.log(count) for index, count in counts.items()}
        norm = math.sqrt(sum(value * value for value in weighted.values())) or 1.0
        return {index: value / norm for index, value in weighted.items()}

    async def upsert(self, chunks: list[ChunkRecord]) -> None:
        if not chunks:
            return
        rows = []
        for chunk in chunks:
            row = chunk.model_dump(
                exclude={"content_hash", "published_at"},
                mode="json",
            )
            row["chunk_id"] = str(chunk.chunk_id)
            row["document_id"] = str(chunk.document_id)
            row["source_id"] = str(chunk.source_id)
            row["crawled_at"] = chunk.crawled_at.isoformat()
            row["section_title"] = chunk.section_title or ""
            row["country_or_region"] = chunk.country_or_region or ""
            row["business_category"] = chunk.business_category or ""
            if self._sparse_mode == "ip":
                row["sparse_vector"] = self._hashed_sparse_vector(chunk.content)
            rows.append(row)
        await asyncio.to_thread(
            self.client.upsert,
            collection_name=self.collection_name,
            data=rows,
        )

    async def delete_document(self, document_id: UUID) -> None:
        expression = f'document_id == "{document_id}"'
        await asyncio.to_thread(
            self.client.delete,
            collection_name=self.collection_name,
            filter=expression,
        )

    @classmethod
    def build_filter_expression(cls, filters: dict[str, object]) -> str:
        """Build a Milvus expression from allow-listed fields and scalar values."""
        clauses = ["is_active == true"]
        for field, value in filters.items():
            if field not in cls.FILTER_FIELDS or value is None or field == "is_active":
                continue
            values = value if isinstance(value, list) else [value]
            if not values:
                continue
            if field == "version":
                safe_values = [str(int(item)) for item in values]
            else:
                safe_values = [
                    '"' + str(item).replace("\\", "\\\\").replace('"', '\\"') + '"'
                    for item in values
                ]
            clauses.append(f"{field} in [{', '.join(safe_values)}]")
        return " and ".join(clauses)

    async def hybrid_search(
        self,
        query: str,
        query_vector: list[float],
        *,
        filters: dict[str, object],
        top_k: int,
    ) -> list[RetrievedDocument]:
        return await asyncio.to_thread(
            self._hybrid_search_sync,
            query,
            query_vector,
            filters,
            top_k,
        )

    def _hybrid_search_sync(
        self,
        query: str,
        query_vector: list[float],
        filters: dict[str, object],
        top_k: int,
    ) -> list[RetrievedDocument]:
        from pymilvus import AnnSearchRequest, WeightedRanker

        if self._sparse_mode is None:
            self._sparse_mode = self._detect_sparse_mode()
        expression = self.build_filter_expression(filters)
        dense_request = AnnSearchRequest(
            data=[query_vector],
            anns_field="dense_vector",
            param={"metric_type": "COSINE", "params": {"ef": 64}},
            limit=top_k,
            expr=expression,
        )
        sparse_data = query if self._sparse_mode == "bm25" else self._hashed_sparse_vector(query)
        sparse_metric = "BM25" if self._sparse_mode == "bm25" else "IP"
        sparse_request = AnnSearchRequest(
            data=[sparse_data],
            anns_field="sparse_vector",
            param={"metric_type": sparse_metric},
            limit=top_k,
            expr=expression,
        )
        output_fields = [
            "chunk_id",
            "document_id",
            "source_id",
            "company_name",
            "source_type",
            "title",
            "section_title",
            "source_url",
            "content",
            "language",
            "country_or_region",
            "business_category",
            "version",
            "is_active",
            "crawled_at",
        ]
        results = self.client.hybrid_search(
            collection_name=self.collection_name,
            reqs=[dense_request, sparse_request],
            ranker=WeightedRanker(0.7, 0.3),
            limit=top_k,
            output_fields=output_fields,
        )
        documents: list[RetrievedDocument] = []
        for hit in results[0]:
            entity = hit.get("entity", hit)
            documents.append(
                RetrievedDocument(
                    chunk_id=UUID(entity["chunk_id"]),
                    document_id=UUID(entity["document_id"]),
                    source_id=UUID(entity["source_id"]),
                    company_name=entity["company_name"],
                    source_type=entity["source_type"],
                    title=entity["title"],
                    section_title=entity.get("section_title") or None,
                    source_url=entity["source_url"],
                    content=entity["content"],
                    language=entity["language"],
                    country_or_region=entity.get("country_or_region") or None,
                    business_category=entity.get("business_category") or None,
                    version=int(entity["version"]),
                    is_active=bool(entity["is_active"]),
                    crawled_at=datetime.fromisoformat(entity["crawled_at"]),
                    retrieval_score=float(hit["distance"]),
                )
            )
        return documents
