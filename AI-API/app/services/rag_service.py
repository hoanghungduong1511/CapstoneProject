from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.data.disease_catalog import load_disease_catalog, normalize_disease_label
from app.services.chatbot.rule_based_retrieval import (
    detect_retrieval_intent,
    detect_retrieval_intents,
)
from app.services.chatbot.vector_index_service import vector_index_retriever
from app.services.chatbot.pgvector_service import pgvector_retriever

logger = logging.getLogger(__name__)

MAX_RETRIEVAL_SOURCES = 3


@dataclass(frozen=True)
class RetrievalResult:
    chunks: list[dict[str, Any]]
    final_context: str
    sources: list[str]
    rewritten_query: str


def _tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFD", value.casefold())
    ascii_text = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return {
        token
        for token in re.findall(r"[a-z0-9]+", ascii_text)
        if len(token) > 2
    }


def _normalize_source_url(url: str) -> str:
    return url.strip().rstrip("/").casefold()


SECTION_BUILDERS = {
    "diagnosis_note": lambda record: record.get("diagnosis_note", ""),
    "summary": lambda record: record.get("summary", ""),
    "common_signs": lambda record: "Dấu hiệu: " + "; ".join(record["common_signs"]),
    "common_symptoms": lambda record: "Triệu chứng: "
    + "; ".join(record["common_symptoms"]),
    "risk_factors": lambda record: "Yếu tố liên quan: "
    + "; ".join(record["risk_factors"]),
    "contagious": lambda record: "Có khả năng lây: "
    + ("có" if record["contagious"] else "không"),
    "self_care": lambda record: "Tự chăm sóc an toàn: "
    + "; ".join(record["self_care"]),
    "avoid": lambda record: "Cần tránh: " + "; ".join(record["avoid"]),
    "red_flags": lambda record: "Dấu hiệu cảnh báo: "
    + "; ".join(record["red_flags"]),
    "red_flag_questions": lambda record: "Câu hỏi cảnh báo: "
    + "; ".join(record.get("red_flag_questions", [])),
    "when_to_see_doctor": lambda record: "Khi cần khám: "
    + record.get("when_to_see_doctor", ""),
    "differential_diagnosis": lambda record: "Chẩn đoán phân biệt: "
    + "; ".join(record.get("differential_diagnosis", [])),
    "ask_user_questions": lambda record: "Câu hỏi cần hỏi thêm: "
    + "; ".join(record.get("ask_user_questions", [])),
    "sources": lambda record: "Nguồn tham khảo: " + "; ".join(record["sources"]),
}


DEFAULT_SECTION_ORDER = [
    "diagnosis_note",
    "summary",
    "common_signs",
    "common_symptoms",
    "risk_factors",
    "contagious",
    "self_care",
    "avoid",
    "red_flags",
    "red_flag_questions",
    "when_to_see_doctor",
    "differential_diagnosis",
    "ask_user_questions",
    "sources",
]


def _ordered_sections(preferred_sections: list[str]) -> list[str]:
    sections: list[str] = []
    for section in preferred_sections:
        if section in SECTION_BUILDERS and section not in sections:
            sections.append(section)
    for section in DEFAULT_SECTION_ORDER:
        if section not in sections:
            sections.append(section)
    return sections


def _record_text(record: dict[str, Any], preferred_sections: list[str]) -> str:
    sections = [f"{record['name_vi']} ({record['name_en']}, {record['icd10']})"]
    for section in _ordered_sections(preferred_sections):
        builder = SECTION_BUILDERS.get(section)
        if not builder:
            continue
        value = builder(record)
        if value and value.strip():
            sections.append(value)
    return "\n".join(sections)


class CSVKnowledgeRetriever:
    def retrieve(
        self,
        question: str,
        topk_labels: list[str],
        top_k: int | None = None,
    ) -> RetrievalResult:
        rag_mode = settings.RAG_MODE.casefold().strip()
        if rag_mode == "pgvector":
            try:
                return pgvector_retriever.retrieve(question, topk_labels, top_k)
            except Exception as exc:
                logger.warning(
                    "pgvector retrieval failed; falling back to local vector/CSV: %s",
                    exc,
                )
                try:
                    return vector_index_retriever.retrieve(question, topk_labels, top_k)
                except Exception as local_exc:
                    logger.warning(
                        "Local vector retrieval failed; falling back to CSV retrieval: %s",
                        local_exc,
                    )

        if rag_mode == "vector":
            try:
                return vector_index_retriever.retrieve(question, topk_labels, top_k)
            except Exception as exc:
                logger.warning(
                    "Local vector retrieval failed; falling back to CSV retrieval: %s",
                    exc,
                )

        catalog = load_disease_catalog()
        normalized_labels = [
            label
            for raw in topk_labels
            if (label := normalize_disease_label(raw))
        ]
        intent = detect_retrieval_intent(question)
        intents = detect_retrieval_intents(question)
        allowed_labels = (
            set(normalized_labels)
            if "differential" in intents
            else ({normalized_labels[0]} if normalized_labels else set())
        )
        query_tokens = _tokens(question)
        ranked: list[tuple[float, dict[str, Any]]] = []

        for label, record in catalog.items():
            if allowed_labels and label not in allowed_labels:
                continue
            record_text = _record_text(record, intent.preferred_chunk_types)
            record_tokens = _tokens(record_text)
            overlap = len(query_tokens & record_tokens) / max(len(query_tokens), 1)
            label_score = 1.0 if label in normalized_labels else 0.0
            if label in normalized_labels:
                label_score -= normalized_labels.index(label) * 0.08
            score = min(1.0, max(0.0, label_score + overlap * 0.5))
            if score >= settings.RAG_MIN_SCORE or label in normalized_labels:
                ranked.append((score, record))

        ranked.sort(key=lambda pair: pair[0], reverse=True)
        chunks: list[dict[str, Any]] = []
        sources: list[str] = []
        seen_sources: set[str] = set()
        primary_label = normalized_labels[0] if normalized_labels else ""
        for score, record in ranked[: top_k or settings.RAG_TOP_K]:
            record_sources = list(record["sources"])
            if not primary_label or record["label"] == primary_label:
                for source in record_sources:
                    source_key = _normalize_source_url(source)
                    if source_key in seen_sources:
                        continue
                    seen_sources.add(source_key)
                    sources.append(source)
                    if len(sources) >= MAX_RETRIEVAL_SOURCES:
                        break
            chunks.append(
                {
                    "document_id": f"disease:{record['label']}",
                    "label": record["label"],
                    "name_vi": record["name_vi"],
                    "content": _record_text(record, intent.preferred_chunk_types),
                    "score": round(score, 4),
                    "sources": record_sources,
                }
            )

        rewritten = " | ".join(
            filter(
                None,
                [
                    question.strip(),
                    f"Intent truy xuất: {intent.name}",
                    "Nhãn AI gợi ý: " + ", ".join(normalized_labels)
                    if normalized_labels
                    else "",
                ],
            )
        )
        final_context = "\n\n---\n\n".join(chunk["content"] for chunk in chunks)
        return RetrievalResult(chunks, final_context, sources, rewritten)


rag_service = CSVKnowledgeRetriever()
