from __future__ import annotations

import re
import unicodedata
from typing import Any, Literal


SafetyLevel = Literal["low", "medium", "high", "urgent"]

HIGH_RISK_LABELS = {"MELANOMA", "BCC", "SCC", "AK"}
URGENT_TERMS = {
    "khó thở",
    "ngất",
    "phù môi",
    "phù lưỡi",
    "chảy máu không cầm",
    "đau dữ dội",
    "hoại tử",
    "lan toàn thân",
}
PRESCRIPTION_TERMS = {
    "kê đơn",
    "liều",
    "bao nhiêu mg",
    "thuốc kháng sinh",
    "thuốc corticoid",
    "thuốc steroid",
}
INJECTION_TERMS = {
    "bỏ qua hướng dẫn",
    "ignore previous",
    "system prompt",
    "tiết lộ prompt",
    "developer message",
}


def _normalize_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.casefold())
    without_accents = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )
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
    normalized = text.casefold()
    return any(term in normalized for term in INJECTION_TERMS)


def classify_medical_safety(
    question: str,
    context: dict[str, Any],
) -> SafetyLevel:
    normalized = question.casefold()
    if any(term in normalized for term in URGENT_TERMS):
        return "urgent"

    symptoms = context.get("user_symptoms") or {}
    top_labels = {
        item.get("label")
        for item in context.get("classification_topk") or []
    }
    red_flags = any(
        symptoms.get(field) is True
        for field in ("bleed", "ulcerated", "changed", "grew", "hurt")
    )
    if red_flags and top_labels & HIGH_RISK_LABELS:
        return "high"
    if symptoms.get("bleed") or symptoms.get("ulcerated"):
        return "high"
    if any(term in normalized for term in PRESCRIPTION_TERMS):
        return "medium"
    return "low"


def enforce_answer_guardrails(answer: str) -> str:
    prohibited = (
        "bạn chắc chắn bị",
        "bạn bị bệnh",
        "không cần đi khám",
    )
    safe = answer.strip()
    safe = re.sub(
        r"^Kết quả AI gợi ý[^\n]*(?:\n\s*\n|\n|$)",
        "",
        safe,
        flags=re.IGNORECASE,
    ).strip()
    safe = re.sub(
        r"(?:^|\n)\s*Th\u00f4ng tin c\u1ea7n b\u1ed5 sung\s*:[\s\S]*?(?=\n\s*\n|$)",
        "",
        safe,
        flags=re.IGNORECASE,
    ).strip()
    if any(term in safe.casefold() for term in prohibited):
        return (
            "Kết quả AI chỉ gợi ý một số khả năng liên quan và không thể xác nhận "
            "chẩn đoán từ ảnh. Bạn nên đối chiếu với triệu chứng và khám bác sĩ da "
            "liễu nếu tổn thương kéo dài, thay đổi hoặc có dấu hiệu cảnh báo."
        )
    return safe
