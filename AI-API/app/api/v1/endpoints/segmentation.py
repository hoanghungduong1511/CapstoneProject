"""
Segmentation Endpoint
Phân vùng tổn thương da từ ảnh upload.
"""

import base64
import io
import time
import logging

import cv2
import numpy as np
from fastapi import APIRouter, File, UploadFile, HTTPException

from app.config import settings
from app.schemas.responses import SegmentationResponse, ErrorResponse
from app.services.model_manager import model_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/segment", tags=["🎯 Segmentation"])


def _encode_image_base64(image: np.ndarray, is_mask: bool = False) -> str:
    """Encode numpy image thành base64 PNG string."""
    if is_mask:
        # Mask nhị phân (0/1) → scale lên 255
        img_to_encode = (image * 255).astype(np.uint8)
    else:
        # RGB image → chuyển sang BGR cho OpenCV
        img_to_encode = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    success, buffer = cv2.imencode(".png", img_to_encode)
    if not success:
        raise ValueError("Failed to encode image to PNG")

    return base64.b64encode(buffer).decode("utf-8")


@router.post(
    "",
    response_model=SegmentationResponse,
    responses={
        400: {"model": ErrorResponse, "description": "File không hợp lệ"},
        503: {"model": ErrorResponse, "description": "Model chưa sẵn sàng"},
    },
    summary="Phân vùng tổn thương da",
    description="""
    Upload ảnh da để **khoanh vùng tổn thương** (skin lesion segmentation).

    **Model:** U-Net + EfficientNet-B3

    **Input:** File ảnh da (JPEG, PNG, WebP, BMP, TIFF) — tối đa 10MB

    **Output:**
    - `lesion_ratio`: Tỷ lệ vùng tổn thương / toàn ảnh (0.0 - 1.0)
    - `bbox`: Bounding box [x_min, y_min, x_max, y_max]
    - `mask_base64`: Binary mask dạng PNG base64
    - `roi_base64`: Vùng tổn thương đã crop dạng PNG base64
    - `fallback`: True nếu không phát hiện tổn thương
    
    **Lưu ý:** Nên chạy qua `/api/v1/validate-skin` trước để đảm bảo ảnh là da người.
    Hoặc dùng `/api/v1/analyze` để chạy full pipeline tự động.
    """,
)
async def segment_skin(
    file: UploadFile = File(..., description="File ảnh da cần phân vùng"),
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
    if model_manager.segmentation is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "model_not_ready",
                "detail": "Segmentation model chưa được load. Kiểm tra /health",
            },
        )

    # ── Predict ──────────────────────────────────────────────────
    try:
        start = time.time()
        result = model_manager.segmentation.predict_from_bytes(image_bytes)
        elapsed_ms = (time.time() - start) * 1000

        # Encode mask và ROI thành base64
        mask_b64 = _encode_image_base64(result["mask"], is_mask=True)
        roi_b64 = _encode_image_base64(result["roi_crop"], is_mask=False)

        logger.info(
            f"Segmentation: lesion={result['lesion_ratio']:.2%}, "
            f"fallback={result['fallback']}, time={elapsed_ms:.0f}ms "
            f"— {file.filename}"
        )

        return SegmentationResponse(
            lesion_ratio=round(result["lesion_ratio"], 4),
            bbox=list(result["bbox"]),
            fallback=result["fallback"],
            mask_base64=mask_b64,
            roi_base64=roi_b64,
            processing_time_ms=round(elapsed_ms, 1),
        )

    except Exception as e:
        logger.error(f"Segmentation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "prediction_failed",
                "detail": f"Lỗi khi phân vùng ảnh: {str(e)}",
            },
        )
