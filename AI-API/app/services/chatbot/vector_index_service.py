from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from app.config import settings
from app.data.disease_catalog import normalize_disease_label
from app.services.chatbot.rule_based_retrieval import (
    detect_retrieval_intents,
    intent_chunk_boost,
)

logger = logging.getLogger(__name__)

MAX_RETRIEVAL_SOURCES = 3


def normalize_embeddings(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def normalize_source_url(url: str) -> str:
    return url.strip().rstrip("/").casefold()


@dataclass(frozen=True)
class VectorSearchResult:
    chunks: list[dict[str, Any]]
    final_context: str
    sources: list[str]
    rewritten_query: str


class SentenceTransformerQueryEmbedder:
    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. Install it with "
                "`pip install sentence-transformers`."
            ) from exc
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    def encode_query(self, query: str) -> np.ndarray:
        vector = self._model.encode(
            [query],
            batch_size=1,
            convert_to_numpy=True,
            normalize_embeddings=False,
            show_progress_bar=False,
        )
        return normalize_embeddings(np.asarray(vector, dtype=np.float32))[0]


@lru_cache(maxsize=2)
def _load_chunks(path: str) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                chunks.append(json.loads(line))
    return chunks


@lru_cache(maxsize=2)
def _load_embeddings(path: str) -> np.ndarray:
    return np.load(path).astype(np.float32)


@lru_cache(maxsize=2)
def _load_config(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@lru_cache(maxsize=2)
def _load_embedder(provider: str, model_name: str):
    if provider == "sentence-transformers":
        return SentenceTransformerQueryEmbedder(model_name)
    raise RuntimeError(f"Unsupported local vector provider: {provider}")


class LocalVectorIndexRetriever:
    def __init__(self, index_dir: str | None = None) -> None:
        self.index_dir = Path(index_dir or settings.VECTOR_INDEX_DIR)

    def _paths(self) -> tuple[Path, Path, Path]:
        config_path = self.index_dir / "index_config.json"
        if not config_path.is_file():
            raise FileNotFoundError(f"Vector index config not found: {config_path}")
        config = _load_config(str(config_path))
        chunks_path = self.index_dir / config["chunks_file"]
        embeddings_path = self.index_dir / config["embeddings_file"]
        if not chunks_path.is_file():
            raise FileNotFoundError(f"Vector chunks file not found: {chunks_path}")
        if not embeddings_path.is_file():
            raise FileNotFoundError(f"Vector embeddings file not found: {embeddings_path}")
        return config_path, chunks_path, embeddings_path

    def is_available(self) -> bool:
        try:
            self._paths()
            return True
        except Exception:
            return False

    def retrieve(
        self,
        question: str,
        topk_labels: list[str],
        top_k: int | None = None,
    ) -> VectorSearchResult:
        config_path, chunks_path, embeddings_path = self._paths()
        config = _load_config(str(config_path))
        chunks = _load_chunks(str(chunks_path))
        embeddings = _load_embeddings(str(embeddings_path))
        if embeddings.shape[0] != len(chunks):
            raise RuntimeError(
                "Vector index is inconsistent: embeddings rows do not match chunks."
            )

        embedder = _load_embedder(config["provider"], config["model"])
        query_vector = embedder.encode_query(question or "")
        vector_scores = embeddings @ query_vector

        normalized_labels = [
            label
            for raw in topk_labels
            if (label := normalize_disease_label(raw))
        ]
        intents = detect_retrieval_intents(question)
        if "differential" in intents:
            allowed = set(normalized_labels)
        else:
            allowed = {normalized_labels[0]} if normalized_labels else set()
        candidates: list[tuple[int, float]] = []
        for index, chunk in enumerate(chunks):
            label = str(chunk.get("label") or "").upper()
            if allowed and label not in allowed:
                continue

            score = float(vector_scores[index])
            if label in normalized_labels:
                score += max(0.16 - normalized_labels.index(label) * 0.035, 0.04)
            score += intent_chunk_boost(
                question,
                str(chunk.get("chunk_type") or ""),
                base_boost=0.22,
            )
            candidates.append((index, score))

        candidates.sort(key=lambda item: item[1], reverse=True)
        selected = candidates[: top_k or settings.RAG_TOP_K]
        result_chunks: list[dict[str, Any]] = []
        sources: list[str] = []
        seen_sources: set[str] = set()
        primary_label = normalized_labels[0] if normalized_labels else ""

        for index, score in selected:
            chunk = chunks[index]
            label = str(chunk.get("label") or "").upper()
            source_urls = [
                source.strip()
                for source in str(chunk.get("source_url") or "").split("|")
                if source.strip()
            ]
            if not primary_label or label == primary_label:
                for source in source_urls:
                    source_key = normalize_source_url(source)
                    if source_key in seen_sources:
                        continue
                    seen_sources.add(source_key)
                    sources.append(source)
                    if len(sources) >= MAX_RETRIEVAL_SOURCES:
                        break
            result_chunks.append(
                {
                    "document_id": str(chunk.get("chunk_id") or f"chunk:{index}"),
                    "label": label,
                    "name_vi": str(chunk.get("disease_name") or ""),
                    "content": str(chunk.get("content") or ""),
                    "score": round(score, 4),
                    "sources": source_urls,
                    "chunk_type": chunk.get("chunk_type"),
                    "chunk_title": chunk.get("chunk_title"),
                    "vector_score": round(float(vector_scores[index]), 4),
                }
            )

        rewritten = " | ".join(
            filter(
                None,
                [
                    question.strip(),
                    "RAG: local-vector-index",
                    "Nhãn AI gợi ý: " + ", ".join(normalized_labels)
                    if normalized_labels
                    else "",
                ],
            )
        )
        return VectorSearchResult(
            chunks=result_chunks,
            final_context="\n\n---\n\n".join(
                chunk["content"] for chunk in result_chunks
            ),
            sources=sources,
            rewritten_query=rewritten,
        )


vector_index_retriever = LocalVectorIndexRetriever()
