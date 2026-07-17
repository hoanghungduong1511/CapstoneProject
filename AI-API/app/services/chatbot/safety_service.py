from __future__ import annotations

import re
import unicodedata
from typing import Any, Literal

from .prompt_templates import load_medical_safety_rules, load_prompt_injection_rules


SafetyLevel = Literal["low", "medium", "high", "urgent"]


def _normalize_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.casefold())
    without_accents = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    ).replace("đ", "d")
    return re.sub(r"\s+", " ", without_accents).strip()


def _detect_boolean_symptom(
    text: str,
    keywords: tuple[str, ...],
) -> bool | None:
    for keyword in keywords:
        if keyword not in text:
            continue
        negative_patterns = (
            rf"\bkhong\s+(?:bi\s+|co\s+)?{re.escape(keyword)}\b",
            rf"\bchua\s+(?:bi\s+|co\s+)?{re.escape(keyword)}\b",
        )
        if any(re.search(pattern, text) for pattern in negative_patterns):
            return False
        return True
    return None


def infer_symptom_updates(text: str) -> dict[str, bool]:
    normalized = _normalize_text(text)
    symptom_keywords = {
        "bleed": ("chay mau", "ra mau"),
        "ulcerated": ("vet loet", "loet"),
        "hurt": ("dau rat", "dau nhuc", "dau"),
        "itch": ("ngua",),
        "grew": ("lon nhanh", "to nhanh", "phat trien nhanh"),
        "changed": (
            "thay doi kich thuoc",
            "doi kich thuoc",
            "thay doi mau",
            "doi mau",
        ),
    }
    updates: dict[str, bool] = {}
    for field, keywords in symptom_keywords.items():
        value = _detect_boolean_symptom(normalized, keywords)
        if value is not None:
            updates[field] = value

    if updates.get("grew") is True:
        updates["changed"] = True
    return updates


def has_prompt_injection(text: str) -> bool:
    normalized = _normalize_text(text)
    rules = load_prompt_injection_rules()
    patterns = [_normalize_text(str(item)) for item in rules.get("patterns", [])]
    return any(pattern and pattern in normalized for pattern in patterns)


def classify_medical_safety(
    question: str,
    context: dict[str, Any],
) -> SafetyLevel:
    normalized = _normalize_text(question)
    rules = load_medical_safety_rules()
    urgent_terms = [_normalize_text(str(item)) for item in rules.get("urgent_terms", [])]
    if any(term and term in normalized for term in urgent_terms):
        return "urgent"

    symptoms = context.get("user_symptoms") or {}
    top_labels = {
        item.get("label")
        for item in context.get("classification_topk") or []
    }
    high_risk_labels = set(rules.get("high_risk_labels", []))
    red_flag_fields = tuple(rules.get("red_flag_symptoms", []))
    red_flags = any(symptoms.get(field) is True for field in red_flag_fields)

    if red_flags and top_labels & high_risk_labels:
        return "high"
    if symptoms.get("bleed") or symptoms.get("ulcerated"):
        return "high"
    if any(term in normalized for term in ("ke don", "lieu", "bao nhieu mg")):
        return "medium"
    return "low"


def enforce_answer_guardrails(answer: str) -> str:
    rules = load_medical_safety_rules()
    blocked_claims = [
        _normalize_text(str(item))
        for item in rules.get("blocked_claims", [])
    ]
    normalized_answer = _normalize_text(answer)
    if any(term and term in normalized_answer for term in blocked_claims):
        return (
            "Kết quả AI chỉ gợi ý một số khả năng liên quan và không thể xác nhận "
            "chẩn đoán từ ảnh. Bạn nên đối chiếu với triệu chứng và khám bác sĩ "
            "da liễu nếu tổn thương kéo dài, thay đổi hoặc có dấu hiệu cảnh báo."
        )
    return answer.strip()

