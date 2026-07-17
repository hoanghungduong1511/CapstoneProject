from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.ai_result import AIResult
from app.models.medical_context import MedicalContext


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


def _topk(ai_result: AIResult) -> list[dict[str, Any]]:
    classification = ai_result.classification_result
    if not classification:
        return []
    items = classification.topk or []
    normalized = []
    for item in items[:10]:
        label = str(item.get("label") or item.get("class_name") or "").upper()
        if not label:
            continue
        normalized.append(
            {
                "label": label,
                "confidence": item.get("confidence", item.get("probability")),
            }
        )
    if not normalized and classification.top1_label:
        normalized.append(
            {
                "label": classification.top1_label.upper(),
                "confidence": classification.top1_confidence,
            }
        )
    return normalized


def _missing_questions(
    symptoms: dict[str, Any],
    labels: list[str],
) -> list[str]:
    priority = ["bleed", "changed", "duration", "hurt", "itch", "body_site"]
    if set(labels) & HIGH_RISK_LABELS:
        priority.insert(2, "skin_cancer_history")
    questions = dict(QUESTION_MAP)
    return [
        questions[key]
        for key in priority
        if symptoms.get(key) is None or symptoms.get(key) == ""
    ][:4]


def build_medical_context(
    db: Session,
    user_id: UUID,
    ai_result_id: UUID,
    user_symptoms: dict[str, Any] | None,
) -> MedicalContext:
    ai_result = (
        db.query(AIResult)
        .filter(AIResult.id == ai_result_id, AIResult.user_id == user_id)
        .first()
    )
    if not ai_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy kết quả phân tích của người dùng.",
        )

    validation = ai_result.input_validation
    image_valid = bool(validation and validation.is_valid)
    topk = _topk(ai_result) if image_valid else []
    segmentation = ai_result.segmentation_result
    ai_feature = ai_result.ai_feature
    symptoms = dict(user_symptoms or {})
    labels = [item["label"] for item in topk]
    missing = _missing_questions(symptoms, labels) if image_valid else []

    segmentation_summary = {
        "lesion_area_percent": (
            segmentation.lesion_area_percent if segmentation else None
        ),
        "mask_available": bool(segmentation and segmentation.mask_url),
        "roi_available": bool(segmentation and segmentation.roi_url),
    }
    ai_features = {
        "feature_vector": ai_feature.feature_vector if ai_feature else None,
    }
    risk_summary = (
        "Cần ưu tiên đánh giá trực tiếp vì AI gợi ý nhóm tổn thương cần loại trừ."
        if set(labels) & HIGH_RISK_LABELS
        else "Chưa ghi nhận nhóm nhãn cần ưu tiên cao từ top-k."
    )
    context_json = {
        "image_valid": image_valid,
        "validation_confidence": validation.confidence if validation else None,
        "classification_topk": topk,
        "segmentation_summary": segmentation_summary,
        "ai_features": ai_features,
        "user_symptoms": symptoms,
        "risk_summary": risk_summary,
        "missing_questions": missing,
    }

    context = (
        db.query(MedicalContext)
        .filter(MedicalContext.ai_result_id == ai_result_id)
        .first()
    )
    if not context:
        context = MedicalContext(ai_result_id=ai_result_id)
        db.add(context)

    context.context_json = context_json
    context.image_valid = image_valid
    context.classification_topk_json = topk
    context.segmentation_summary_json = segmentation_summary
    context.ai_features_json = ai_features
    context.user_symptoms_json = symptoms
    context.risk_summary = risk_summary
    context.missing_questions_json = missing
    db.flush()
    return context
