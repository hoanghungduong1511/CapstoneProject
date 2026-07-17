"""
Pydantic Schemas — Response models cho tất cả API endpoints.
Chuẩn hóa format response và tự động sinh Swagger documentation.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════

class ModelStatus(BaseModel):
    """Trạng thái của 1 model."""
    loaded: bool = Field(..., description="Model đã load thành công chưa")
    architecture: str = Field(..., description="Kiến trúc model (vd: EfficientNet-B0)")
    task: str = Field(..., description="Nhiệm vụ của model")
    load_time_s: Optional[float] = Field(None, description="Thời gian load model (giây)")

    model_config = {"json_schema_extra": {
        "example": {
            "loaded": True,
            "architecture": "EfficientNet-B0",
            "task": "Binary Classification (skin / not-skin)",
            "load_time_s": 1.23,
        }
    }}


class ModelsHealth(BaseModel):
    """Trạng thái của tất cả models."""
    skin_validation: ModelStatus
    segmentation: ModelStatus
    classification: ModelStatus


class HealthResponse(BaseModel):
    """Response cho GET /health."""
    status: str = Field(..., description="Trạng thái service", examples=["ok"])
    service: str = Field(..., description="Tên service")
    version: str = Field(..., description="Phiên bản API")
    device: str = Field(..., description="Device đang sử dụng (cuda/cpu)")
    models: ModelsHealth


# ═══════════════════════════════════════════════════════════════════════
#  SKIN VALIDATION
# ═══════════════════════════════════════════════════════════════════════

class SkinValidationResponse(BaseModel):
    """Response cho POST /api/v1/validate-skin."""
    is_skin: bool = Field(..., description="Ảnh có phải da người không")
    confidence: float = Field(..., ge=0, le=1, description="Độ tin cậy (0.0 - 1.0)")
    class_name: str = Field(..., description="Tên lớp: person_skin hoặc non_person_skin")
    probability: float = Field(..., ge=0, le=1, description="Xác suất là da người (0.0 - 1.0)")
    threshold: float = Field(..., description="Ngưỡng quyết định")
    processing_time_ms: float = Field(..., description="Thời gian xử lý (ms)")

    model_config = {"json_schema_extra": {
        "example": {
            "is_skin": True,
            "confidence": 0.97,
            "class_name": "person_skin",
            "probability": 0.97,
            "threshold": 0.5,
            "processing_time_ms": 120.5,
        }
    }}


# ═══════════════════════════════════════════════════════════════════════
#  SEGMENTATION
# ═══════════════════════════════════════════════════════════════════════

class SegmentationResponse(BaseModel):
    """Response cho POST /api/v1/segment."""
    lesion_ratio: float = Field(..., ge=0, le=1, description="Tỷ lệ vùng tổn thương / toàn ảnh")
    bbox: List[int] = Field(..., description="Bounding box [x_min, y_min, x_max, y_max]")
    fallback: bool = Field(..., description="True nếu không phát hiện tổn thương, dùng toàn bộ ảnh")
    mask_base64: str = Field(..., description="Binary mask (PNG, base64 encoded)")
    roi_base64: str = Field(..., description="Cropped ROI (PNG, base64 encoded)")
    processing_time_ms: float = Field(..., description="Thời gian xử lý (ms)")

    model_config = {"json_schema_extra": {
        "example": {
            "lesion_ratio": 0.15,
            "bbox": [50, 30, 200, 180],
            "fallback": False,
            "mask_base64": "<base64 encoded PNG>",
            "roi_base64": "<base64 encoded PNG>",
            "processing_time_ms": 350.2,
        }
    }}


# ═══════════════════════════════════════════════════════════════════════
#  FULL PIPELINE
# ═══════════════════════════════════════════════════════════════════════

class PipelineValidation(BaseModel):
    """Kết quả validation trong full pipeline."""
    is_skin: bool
    confidence: float
    class_name: str
    probability: float
    threshold: float


class PipelineSegmentation(BaseModel):
    """Kết quả segmentation trong full pipeline."""
    lesion_ratio: float
    bbox: List[int]
    fallback: bool
    mask_base64: str
    roi_base64: str


class ClassificationCandidate(BaseModel):
    label: str
    confidence: float


class PipelineClassification(BaseModel):
    top_label: str
    top_confidence: float
    candidates: List[ClassificationCandidate]


class PipelineResponse(BaseModel):
    """Response cho POST /api/v1/analyze — Full pipeline."""
    accepted: bool = Field(..., description="Ảnh có được chấp nhận (là da người) không")
    message: str = Field(..., description="Thông báo kết quả")
    validation: PipelineValidation = Field(..., description="Kết quả validate skin")
    segmentation: Optional[PipelineSegmentation] = Field(
        None, description="Kết quả segmentation (null nếu không phải da)"
    )
    classification: Optional[PipelineClassification] = None
    processing_time_ms: float = Field(..., description="Tổng thời gian xử lý (ms)")

    model_config = {"json_schema_extra": {
        "example": {
            "accepted": True,
            "message": "Ảnh hợp lệ — đã phân vùng tổn thương da",
            "validation": {
                "is_skin": True,
                "confidence": 0.97,
                "class_name": "person_skin",
                "probability": 0.97,
                "threshold": 0.5,
            },
            "segmentation": {
                "lesion_ratio": 0.15,
                "bbox": [50, 30, 200, 180],
                "fallback": False,
                "mask_base64": "<base64>",
                "roi_base64": "<base64>",
            },
            "processing_time_ms": 450.8,
        }
    }}


# ═══════════════════════════════════════════════════════════════════════
#  ERROR
# ═══════════════════════════════════════════════════════════════════════

class ErrorResponse(BaseModel):
    """Response lỗi chuẩn hóa."""
    error: str = Field(..., description="Mã lỗi ngắn gọn")
    detail: str = Field(..., description="Mô tả chi tiết lỗi")

    model_config = {"json_schema_extra": {
        "example": {
            "error": "invalid_image",
            "detail": "Chỉ chấp nhận file ảnh (JPEG, PNG, WebP, BMP, TIFF)",
        }
    }}
