"""
Skin Validation Endpoint
Kiểm tra ảnh upload có phải da người hay không (Skin Gate).
"""

import time
import logging

from fastapi import APIRouter, File, UploadFile, HTTPException

from app.config import settings
from app.schemas.responses import SkinValidationResponse, ErrorResponse
from app.services.model_manager import model_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/validate-skin", tags=["🔍 Skin Validation"])


@router.post(
    "",
    response_model=SkinValidationResponse,
    responses={
        400: {"model": ErrorResponse, "description": "File không hợp lệ"},
        503: {"model": ErrorResponse, "description": "Model chưa sẵn sàng"},
    },
    summary="Kiểm tra ảnh có phải da người không",
    description="""
    Upload ảnh để kiểm tra có phải **da người** hay không.

    **Model:** EfficientNet-B0 (Binary Classification)

    **Input:** File ảnh (JPEG, PNG, WebP, BMP, TIFF) — tối đa 10MB

    **Output:**
    - `is_skin`: True/False
    - `confidence`: Độ tin cậy (0.0 - 1.0)
    - `class_name`: `person_skin` hoặc `non_person_skin`
    
    **Ứng dụng:** Dùng làm "cổng kiểm soát" trước khi đưa ảnh vào pipeline phân tích bệnh da.
    """,
)
async def validate_skin(
    file: UploadFile = File(..., description="File ảnh cần kiểm tra"),
):
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

    # ── Check model ready ────────────────────────────────────────
    if model_manager.skin_gate is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "model_not_ready",
                "detail": "Skin Validation model chưa được load. Kiểm tra /health",
            },
        )

    # ── Predict ──────────────────────────────────────────────────
    try:
        start = time.time()
        result = model_manager.skin_gate.predict(image_bytes, use_tta=True)
        elapsed_ms = (time.time() - start) * 1000

        logger.info(
            f"Skin Validation: {result['class_name']} "
            f"(conf={result['confidence']:.3f}, time={elapsed_ms:.0f}ms) "
            f"— {file.filename}"
        )

        return SkinValidationResponse(
            is_skin=result["is_skin"],
            confidence=result["confidence"],
            class_name=result["class_name"],
            probability=result["probability"],
            threshold=result["threshold"],
            processing_time_ms=round(elapsed_ms, 1),
        )

    except Exception as e:
        logger.error(f"Skin Validation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "prediction_failed",
                "detail": f"Lỗi khi phân tích ảnh: {str(e)}",
            },
        )
