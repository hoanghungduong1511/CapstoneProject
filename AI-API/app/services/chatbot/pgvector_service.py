from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.data.disease_catalog import normalize_disease_label
from app.services.chatbot.rule_based_retrieval import (
    detect_retrieval_intents,
    intent_chunk_boost,
)
from app.services.chatbot.vector_index_service import (
    MAX_RETRIEVAL_SOURCES,
    SentenceTransformerQueryEmbedder,
    normalize_source_url,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PgVectorSearchResult:
    chunks: list[dict[str, Any]]
    final_context: str
    sources: list[str]
    rewritten_query: str


def _vector_literal(vector: Any) -> str:
    return "[" + ",".join(f"{float(value):.8f}" for value in vector) + "]"


class PgVectorRetriever:
    def __init__(self) -> None:
        self.table_name = settings.PGVECTOR_TABLE
        self._embedder: SentenceTransformerQueryEmbedder | None = None

    def _database_url(self) -> str:
        if not settings.PGVECTOR_DATABASE_URL:
            raise RuntimeError("PGVECTOR_DATABASE_URL is not configured")
        return settings.PGVECTOR_DATABASE_URL

    def _connect(self):
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError(
                "psycopg is not installed. Install requirements.txt again."
            ) from exc
        return psycopg.connect(self._database_url())

    def _get_embedder(self) -> SentenceTransformerQueryEmbedder:
        if self._embedder is None:
            if settings.PGVECTOR_EMBEDDING_PROVIDER != "sentence-transformers":
                raise RuntimeError(
                    "Only sentence-transformers pgvector embeddings are supported."
                )
            self._embedder = SentenceTransformerQueryEmbedder(
                settings.PGVECTOR_EMBEDDING_MODEL
            )
        return self._embedder

    def is_available(self) -> bool:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT to_regclass(%s)",
                        (self.table_name,),
                    )
                    return cur.fetchone()[0] is not None
        except Exception as exc:
            logger.warning("pgvector retriever is unavailable: %s", exc)
            return False

    def retrieve(
        self,
        question: str,
        topk_labels: list[str],
        top_k: int | None = None,
    ) -> PgVectorSearchResult:
        query_vector = self._get_embedder().encode_query(question or "")
        query_literal = _vector_literal(query_vector)
        normalized_labels = [
            label for raw in topk_labels if (label := normalize_disease_label(raw))
        ]
        intents = detect_retrieval_intents(question)
        if "differential" in intents:
            allowed = set(normalized_labels)
        else:
            allowed = {normalized_labels[0]} if normalized_labels else set()

        fetch_limit = max((top_k or settings.RAG_TOP_K) * 8, 40)
        params: list[Any] = [query_literal]
        where_sql = ""
        if allowed:
            where_sql = "WHERE label = ANY(%s)"
            params.append(list(allowed))
        params.extend([query_literal, fetch_limit])

        sql = f"""
            SELECT
                chunk_id,
                label,
                disease_name,
                content,
                source_url,
                chunk_type,
                chunk_title,
                1 - (embedding <=> %s::vector) AS vector_score
            FROM {self.table_name}
            {where_sql}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """

        rows: list[tuple[Any, ...]] = []
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

        candidates: list[dict[str, Any]] = []
        for row in rows:
            (
                chunk_id,
                label,
                disease_name,
                content,
                source_url,
                chunk_type,
                chunk_title,
                vector_score,
            ) = row
            label = str(label or "").upper()
            score = float(vector_score or 0.0)
            if label in normalized_labels:
                score += max(0.16 - normalized_labels.index(label) * 0.035, 0.04)
            score += intent_chunk_boost(question, str(chunk_type or ""), base_boost=0.22)
            source_urls = [
                source.strip()
                for source in str(source_url or "").split("|")
                if source.strip()
            ]
            candidates.append(
                {
                    "document_id": str(chunk_id or ""),
                    "label": label,
                    "name_vi": str(disease_name or ""),
                    "content": str(content or ""),
                    "score": round(score, 4),
                    "sources": source_urls,
                    "chunk_type": chunk_type,
                    "chunk_title": chunk_title,
                    "vector_score": round(float(vector_score or 0.0), 4),
                }
            )

        candidates.sort(key=lambda item: item["score"], reverse=True)
        result_chunks = candidates[: top_k or settings.RAG_TOP_K]

        sources: list[str] = []
        seen_sources: set[str] = set()
        primary_label = normalized_labels[0] if normalized_labels else ""
        for chunk in result_chunks:
            if primary_label and chunk["label"] != primary_label:
                continue
            for source in chunk.get("sources") or []:
                source_key = normalize_source_url(source)
                if source_key in seen_sources:
                    continue
                seen_sources.add(source_key)
                sources.append(source)
                if len(sources) >= MAX_RETRIEVAL_SOURCES:
                    break
            if len(sources) >= MAX_RETRIEVAL_SOURCES:
                break

        rewritten = " | ".join(
            filter(
                None,
                [
                    question.strip(),
                    "RAG: pgvector",
                    "Nhãn AI gợi ý: " + ", ".join(normalized_labels)
                    if normalized_labels
                    else "",
                ],
            )
        )
        return PgVectorSearchResult(
            chunks=result_chunks,
            final_context="\n\n---\n\n".join(
                chunk["content"] for chunk in result_chunks if chunk.get("content")
            ),
            sources=sources,
            rewritten_query=rewritten,
        )


pgvector_retriever = PgVectorRetriever()
