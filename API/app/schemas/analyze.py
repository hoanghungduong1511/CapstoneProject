"""
Pydantic Schemas — Analyze endpoint request/response.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════
#  RESPONSE: Skin Analysis
# ═══════════════════════════════════════════════════════════════════════

class ValidationResult(BaseModel):
    """Kết quả validate skin."""
    is_skin: bool
    confidence: float
    class_name: str
    probability: float
    threshold: float


class SegmentationDetail(BaseModel):
    """Kết quả segmentation."""
    mask_url: str = Field(..., description="URL ảnh mask trên MinIO")
    roi_url: str = Field(..., description="URL ảnh ROI crop trên MinIO")
    lesion_ratio: float = Field(..., description="Tỷ lệ tổn thương (0-1)")
    bbox: List[int] = Field(..., description="Bounding box [x1,y1,x2,y2]")
    fallback: bool


class ClassificationCandidate(BaseModel):
    id: str
    name: str
    latinName: str
    icd: str
    description: str
    urgency: str
    recommendation: str
    confidence: float


class ClassificationDetail(BaseModel):
    top_id: str
    top_label: str
    top_confidence: float
    candidates: List[ClassificationCandidate]


class SkinAnalysisResponse(BaseModel):
    """Response chính cho POST /api/v1/analyze/skin."""
    accepted: bool = Field(..., description="Ảnh được chấp nhận (là da người)")
    message: str = Field(..., description="Thông báo kết quả")
    original_image_url: str = Field(..., description="URL ảnh gốc trên MinIO")
    validation: ValidationResult
    segmentation: Optional[SegmentationDetail] = None
    classification: Optional[ClassificationDetail] = None
    processing_time_ms: float = Field(..., description="Tổng thời gian xử lý (ms)")

    # DB IDs để FE dùng cho các bước tiếp theo (chat, history, ...)
    image_id: Optional[str] = None
    ai_result_id: Optional[str] = None

    model_config = {"json_schema_extra": {
        "example": {
            "accepted": True,
            "message": "Ảnh hợp lệ — phát hiện tổn thương da (15.2% diện tích).",
            "original_image_url": "http://localhost:9000/skin-diseases-images/skin-images/original/2026/05/28/abc_photo.jpg",
            "validation": {
                "is_skin": True,
                "confidence": 0.97,
                "class_name": "person_skin",
                "probability": 0.97,
                "threshold": 0.5,
            },
            "segmentation": {
                "mask_url": "http://localhost:9000/skin-diseases-images/skin-images/masks/2026/05/28/abc_mask.png",
                "roi_url": "http://localhost:9000/skin-diseases-images/skin-images/roi/2026/05/28/abc_roi.png",
                "lesion_ratio": 0.152,
                "bbox": [50, 30, 200, 180],
                "fallback": False,
            },
            "processing_time_ms": 450.8,
            "image_id": "uuid-string",
            "ai_result_id": "uuid-string",
        }
    }}


class AIHealthResponse(BaseModel):
    """Response cho GET /api/v1/analyze/health."""
    backend_status: str
    ai_service: Optional[dict] = None
