"""
Full Pipeline Endpoint
Chạy toàn bộ pipeline: Validate Skin → Segmentation → Trả kết quả tổng hợp.
"""

import base64
import time
import logging

import cv2
import numpy as np
from fastapi import APIRouter, File, UploadFile, HTTPException

from app.config import settings
from app.schemas.responses import (
    PipelineResponse,
    PipelineValidation,
    PipelineSegmentation,
    PipelineClassification,
    ErrorResponse,
)
from app.services.model_manager import model_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["🚀 Full Pipeline"])


def _encode_image_base64(image: np.ndarray, is_mask: bool = False) -> str:
    """Encode numpy image thành base64 PNG string."""
    if is_mask:
        img_to_encode = (image * 255).astype(np.uint8)
    else:
        img_to_encode = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    success, buffer = cv2.imencode(".png", img_to_encode)
    if not success:
        raise ValueError("Failed to encode image to PNG")

    return base64.b64encode(buffer).decode("utf-8")


@router.post(
    "",
    response_model=PipelineResponse,
    responses={
        400: {"model": ErrorResponse, "description": "File không hợp lệ"},
        503: {"model": ErrorResponse, "description": "Model chưa sẵn sàng"},
    },
    summary="Phân tích ảnh da — Full Pipeline",
    description="""
    **Pipeline hoàn chỉnh** cho phân tích ảnh bệnh da:

    ```
    Upload ảnh → Validate Skin → Segmentation → Kết quả tổng hợp
    ```

    **Bước 1 — Skin Validation:** Kiểm tra ảnh có phải da người không.
    - Nếu **KHÔNG phải da** → trả `accepted: false`, dừng pipeline.

    **Bước 2 — Segmentation:** Khoanh vùng tổn thương.
    - Trả mask, bounding box, ROI crop.

    **Input:** File ảnh (JPEG, PNG, WebP, BMP, TIFF) — tối đa 10MB

    **Ưu điểm so với gọi từng endpoint riêng:**
    - 1 request thay vì 2
    - Tự động skip segmentation nếu ảnh không hợp lệ
    - Trả tổng thời gian xử lý
    """,
)
async def analyze_pipeline(
    file: UploadFile = File(..., description="File ảnh cần phân tích"),
):
    pipeline_start = time.time()

    # ── Validate file type ───────────────────────────────────────
    if file.content_type not in settings.ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_image",
                "detail": f"Chỉ chấp nhận file ảnh ({', '.join(settings.ALLOWED_CONTENT_TYPES)}). "
                          f"Nhận được: {file.content_type}",
            },
        )

    # ── Validate file size ───────────────────────────────────────
    image_bytes = await file.read()
    file_size_mb = len(image_bytes) / (1024 * 1024)

    if file_size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "file_too_large",
                "detail": f"File quá lớn ({file_size_mb:.1f}MB). Tối đa: {settings.MAX_FILE_SIZE_MB}MB",
            },
        )

    # ── Check models ready ───────────────────────────────────────
    if (
        model_manager.skin_gate is None
        or model_manager.segmentation is None
        or model_manager.classification is None
    ):
        missing = []
        if model_manager.skin_gate is None:
            missing.append("skin_validation")
        if model_manager.segmentation is None:
            missing.append("segmentation")
        if model_manager.classification is None:
            missing.append("classification")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "model_not_ready",
                "detail": f"Models chưa sẵn sàng: {', '.join(missing)}. Kiểm tra /health",
            },
        )

    try:
        # ═══════════════════════════════════════════════════════════
        #  STEP 1: SKIN VALIDATION
        # ═══════════════════════════════════════════════════════════
        val_result = model_manager.skin_gate.predict(image_bytes, use_tta=True)

        validation = PipelineValidation(
            is_skin=val_result["is_skin"],
            confidence=val_result["confidence"],
            class_name=val_result["class_name"],
            probability=val_result["probability"],
            threshold=val_result["threshold"],
        )

        # Chấp nhận nếu là da và confidence đủ cao
        min_conf = 0.65
        is_accepted = val_result["is_skin"] and val_result["confidence"] >= min_conf

        if not is_accepted:
            elapsed_ms = (time.time() - pipeline_start) * 1000
            reason = "Ảnh không phải da người" if not val_result["is_skin"] else f"Hình ảnh không rõ ràng (độ tin cậy {val_result['confidence']:.1%} < {min_conf:.1%})"
            logger.info(
                f"Pipeline REJECTED: {reason} "
                f"— {file.filename}"
            )
            return PipelineResponse(
                accepted=False,
                message=f"{reason}. Vui lòng upload ảnh chụp vùng da rõ nét để phân tích.",
                validation=validation,
                segmentation=None,
                classification=None,
                processing_time_ms=round(elapsed_ms, 1),
            )

        # ═══════════════════════════════════════════════════════════
        #  STEP 2: SEGMENTATION
        # ═══════════════════════════════════════════════════════════
        seg_result = model_manager.segmentation.predict_from_bytes(image_bytes)

        mask_b64 = _encode_image_base64(seg_result["mask"], is_mask=True)
        roi_b64 = _encode_image_base64(seg_result["roi_crop"], is_mask=False)

        segmentation = PipelineSegmentation(
            lesion_ratio=round(seg_result["lesion_ratio"], 4),
            bbox=list(seg_result["bbox"]),
            fallback=seg_result["fallback"],
            mask_base64=mask_b64,
            roi_base64=roi_b64,
        )

        classification_input = (
            seg_result["roi_crop"] if not seg_result["fallback"] else image_bytes
        )
        classification = PipelineClassification(
            **model_manager.classification.predict(classification_input, top_k=5)
        )

        elapsed_ms = (time.time() - pipeline_start) * 1000

        # Message dựa vào kết quả
        if seg_result["fallback"]:
            message = "Ảnh hợp lệ — không phát hiện tổn thương rõ ràng, sử dụng toàn bộ ảnh."
        else:
            lesion_pct = seg_result["lesion_ratio"] * 100
            message = f"Ảnh hợp lệ — phát hiện tổn thương da ({lesion_pct:.1f}% diện tích)."

        logger.info(
            f"Pipeline ACCEPTED: lesion={seg_result['lesion_ratio']:.2%}, "
            f"fallback={seg_result['fallback']}, total={elapsed_ms:.0f}ms "
            f"— {file.filename}"
        )

        return PipelineResponse(
            accepted=True,
            message=message,
            validation=validation,
            segmentation=segmentation,
            classification=classification,
            processing_time_ms=round(elapsed_ms, 1),
        )

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "pipeline_failed",
                "detail": f"Lỗi khi phân tích ảnh: {str(e)}",
            },
        )
