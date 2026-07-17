from __future__ import annotations

from typing import Any

from app.data.disease_catalog import normalize_disease_label


QUESTION_MAP = [
    ("duration", "Tổn thương xuất hiện bao lâu rồi?"),
    ("itch", "Vùng da có ngứa không?"),
    ("hurt", "Vùng tổn thương có đau không?"),
    ("bleed", "Tổn thương có chảy máu hoặc loét không?"),
    ("changed", "Tổn thương có lớn nhanh hoặc đổi màu/kích thước không?"),
    ("body_site", "Tổn thương nằm ở vị trí nào trên cơ thể?"),
    ("skin_cancer_history", "Bạn có tiền sử ung thư da không?"),
]

HIGH_RISK_LABELS = {"MELANOMA", "BCC", "SCC", "AK"}


def _normalized_topk(context: dict[str, Any]) -> list[dict[str, Any]]:
    topk = context.get("classification_topk") or context.get("candidates") or []
    normalized = []
    for candidate in topk[:10]:
        label = normalize_disease_label(candidate.get("label"))
        if not label:
            continue
        confidence = candidate.get("confidence", candidate.get("probability"))
        normalized.append({"label": label, "confidence": confidence})
    if not normalized and context.get("top_label"):
        label = normalize_disease_label(context.get("top_label"))
        if label:
            normalized.append(
                {"label": label, "confidence": context.get("top_confidence")}
            )
    return normalized


def select_missing_questions(
    symptoms: dict[str, Any] | None,
    topk_labels: list[str],
    limit: int = 4,
) -> list[str]:
    symptoms = symptoms or {}
    priority = ["bleed", "changed", "duration", "hurt", "itch", "body_site"]
    if any(label in HIGH_RISK_LABELS for label in topk_labels):
        priority.insert(2, "skin_cancer_history")
    questions = dict(QUESTION_MAP)
    missing = [
        questions[key]
        for key in priority
        if symptoms.get(key) is None or symptoms.get(key) == ""
    ]
    return missing[:limit]


def build_medical_context(
    analysis: dict[str, Any] | None,
    user_symptoms: dict[str, Any] | None = None,
) -> dict[str, Any]:
    analysis = analysis or {}
    image_valid = bool(
        analysis.get("image_valid", analysis.get("accepted", True))
    )
    topk = _normalized_topk(analysis) if image_valid else []
    labels = [item["label"] for item in topk]
    symptoms = dict(user_symptoms or {})

    return {
        "image_valid": image_valid,
        "validation_confidence": analysis.get("validation_confidence"),
        "classification_topk": topk,
        "segmentation_summary": {
            "lesion_area_percent": analysis.get(
                "lesion_area_percent", analysis.get("lesion_ratio")
            ),
            "mask_available": bool(analysis.get("mask_available")),
            "fallback": bool(analysis.get("fallback")),
        },
        "ai_features": analysis.get("ai_features") or {},
        "user_profile": analysis.get("user_profile") or {},
        "user_symptoms": symptoms,
        "risk_summary": analysis.get("risk_summary"),
        "missing_questions": (
            select_missing_questions(symptoms, labels) if image_valid else []
        ),
    }

