from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from .prompt_templates import load_retrieval_rules


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    without_accents = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )
    without_accents = without_accents.replace("đ", "d").replace("Đ", "d")
    without_accents = without_accents.replace("Ä‘", "d").replace("Ä", "d")
    without_accents = re.sub(r"[^a-z0-9]+", " ", without_accents)
    return re.sub(r"\s+", " ", without_accents).strip()


@dataclass(frozen=True)
class RetrievalIntent:
    name: str
    preferred_chunk_types: list[str]


INTENT_CHUNK_TYPES = {
    "overview": ["summary", "diagnosis_note"],
    "symptoms": ["common_signs", "common_symptoms", "red_flags"],
    "contagious": ["contagious", "self_care", "avoid"],
    "self_care": ["self_care", "avoid", "when_to_see_doctor", "red_flags"],
    "doctor": ["when_to_see_doctor", "red_flags", "red_flag_questions"],
    "severity": ["red_flags", "when_to_see_doctor", "common_signs"],
    "sources": ["sources"],
    "differential": ["differential_diagnosis"],
    "follow_up": ["ask_user_questions", "red_flag_questions"],
    "unsafe_medication": ["avoid", "when_to_see_doctor", "red_flags"],
    "prompt_injection": [],
    "out_of_scope": [],
}


def _contains_any(normalized_query: str, keywords: tuple[str, ...]) -> bool:
    for keyword in keywords:
        if not keyword:
            continue
        if " " in keyword:
            if keyword in normalized_query:
                return True
            continue
        if re.search(rf"\b{re.escape(keyword)}\b", normalized_query):
            return True
    return False


def detect_retrieval_intents(query: str) -> list[str]:
    normalized_query = normalize_text(query)
    checks = [
        (
            "prompt_injection",
            (
                "bo qua huong dan",
                "ignore previous instructions",
                "in system prompt",
                "system prompt",
                "chan doan chac chan",
                "xac nhan chac chan",
                "chac chan toi bi",
                "bac si that",
                "khong can nguon",
                "khong can di kham",
            ),
        ),
        (
            "out_of_scope",
            (
                "mua dien thoai",
                "lam toan",
                "lam bai toan",
                "viet code khong lien quan",
                "tu van tai chinh",
                "co phieu",
                "thoi tiet",
            ),
        ),
        (
            "unsafe_medication",
            (
                "ke don",
                "lieu dung",
                "lieu thuoc",
                "thuoc manh nhat",
                "uong bao nhieu",
                "boi bao nhieu",
                "boi thuoc gi",
                "uong thuoc gi",
                "tu uong",
                "tu boi",
                "tu dieu tri",
            ),
        ),
        ("sources", ("nguon", "source", "url", "link", "tai lieu", "tham khao")),
        (
            "contagious",
            (
                "lay khong",
                "co lay khong",
                "truyen nhiem",
                "lay cho nguoi khac",
                "dung chung",
            ),
        ),
        (
            "doctor",
            (
                "di kham",
                "bac si",
                "khi nao kham",
                "khi nao nen",
                "co nguy hiem khong",
                "nguy hiem",
                "co sao khong",
            ),
        ),
        (
            "severity",
            (
                "chay mau",
                "loet",
                "lon nhanh",
                "thay doi mau",
                "thay doi kich thuoc",
                "dau nhieu",
                "dau tang",
                "mu",
                "sot",
            ),
        ),
        (
            "symptoms",
            ("trieu chung", "dau hieu", "bieu hien", "nhan biet", "trong nhu the nao"),
        ),
        (
            "self_care",
            (
                "cham soc",
                "tu cham soc",
                "tai nha",
                "dieu tri",
                "cach dieu tri",
                "cach chua",
                "xu tri",
                "nen lam gi",
            ),
        ),
        ("differential", ("phan biet", "giong benh", "giong voi", "nham voi")),
        ("follow_up", ("hoi gi", "can hoi", "thong tin bo sung")),
        (
            "overview",
            ("thong tin", "tong quan", "la gi", "biet them", "giai thich", "benh nay"),
        ),
    ]
    intents: list[str] = []
    for intent, keywords in checks:
        if _contains_any(normalized_query, keywords):
            intents.append(intent)
    if "prompt_injection" in intents:
        return ["prompt_injection"]
    if "out_of_scope" in intents:
        return ["out_of_scope"]
    if "unsafe_medication" in intents:
        return ["unsafe_medication"]
    explicit_overview = any(
        keyword in normalized_query
        for keyword in (
            "thong tin",
            "tong quan",
            "biet them",
            "cho toi biet",
            "giai thich",
            "benh la gi",
            "benh nay la gi",
        )
    )
    if "overview" in intents and any(
        intent in intents for intent in ("symptoms", "self_care")
    ):
        intents = [intent for intent in intents if intent != "overview"]
    if "overview" in intents and len(intents) > 1 and not explicit_overview:
        intents = [intent for intent in intents if intent != "overview"]
    if "sources" in intents and len(intents) > 1:
        intents = [intent for intent in intents if intent != "overview"]
    if not intents:
        intents.append("overview")
    return intents


def chunk_types_for_intents(intents: list[str]) -> list[str]:
    chunk_types: list[str] = []
    for intent in intents:
        for chunk_type in INTENT_CHUNK_TYPES.get(intent, []):
            if chunk_type not in chunk_types:
                chunk_types.append(chunk_type)
    return chunk_types


def detect_retrieval_intent(query: str) -> RetrievalIntent:
    rules = load_retrieval_rules()
    normalized_query = normalize_text(query)
    intents: dict[str, Any] = rules.get("intents", {})
    best_match: tuple[int, str, dict[str, Any]] | None = None

    for name, config in intents.items():
        keywords = [normalize_text(str(item)) for item in config.get("keywords", [])]
        matched_lengths = [
            len(keyword)
            for keyword in keywords
            if keyword and keyword in normalized_query
        ]
        if not matched_lengths:
            continue
        score = max(matched_lengths)
        if best_match is None or score > best_match[0]:
            best_match = (score, name, config)

    multi_intents = detect_retrieval_intents(query)
    if len(multi_intents) > 1:
        return RetrievalIntent(
            name="+".join(multi_intents),
            preferred_chunk_types=chunk_types_for_intents(multi_intents),
        )

    if best_match is not None:
        _, name, config = best_match
        return RetrievalIntent(
            name=name,
            preferred_chunk_types=list(config.get("preferred_chunk_types", [])),
        )

    default_name = str(rules.get("default_intent") or "overview")
    default_config = intents.get(default_name, {})
    return RetrievalIntent(
        name=default_name,
        preferred_chunk_types=list(default_config.get("preferred_chunk_types", [])),
    )


def intent_chunk_boost(query: str, chunk_type: str, base_boost: float = 0.18) -> float:
    intent = detect_retrieval_intent(query)
    if chunk_type not in intent.preferred_chunk_types:
        return 0.0
    rank = intent.preferred_chunk_types.index(chunk_type)
    if intent.name == "overview":
        overview_boosts = {
            "summary": 0.34,
            "common_signs": 0.16,
            "common_symptoms": 0.14,
            "diagnosis_note": 0.10,
        }
        return overview_boosts.get(chunk_type, 0.0)
    return max(base_boost - rank * 0.035, 0.04)
