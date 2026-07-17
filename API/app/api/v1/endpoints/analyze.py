"""
Analyze API — Endpoint phân tích ảnh da qua AI Service.
Yêu cầu đăng nhập (JWT auth).

Flow:
1. User upload ảnh → lưu MinIO (original)
2. Gọi AI Service → validate + segment + classify
3. Lưu mask + ROI vào MinIO
4. Lưu metadata vào DB
5. Trả kết quả về FE
"""

import base64
import io
import time
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.image import Image
from app.models.ai_result import AIResult
from app.models.input_validation import InputValidation
from app.models.segmentation_result import SegmentationResult
from app.models.classification_result import ClassificationResult as DBClassificationResult
from app.schemas.analyze import (
    SkinAnalysisResponse,
    ValidationResult,
    SegmentationDetail,
    ClassificationDetail,
    AIHealthResponse,
)
from app.services.ai_service import (
    call_ai_analyze,
    call_ai_classify,
    check_ai_health,
    AIServiceError,
)
from app.services.minio_service import get_minio_client, get_file_url, _ensure_bucket, _generate_object_name

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["🔬 Skin Analysis"])

# ── Allowed image types ──────────────────────────────────────────────
ALLOWED_CONTENT_TYPES = [
    "image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff",
]
MAX_FILE_SIZE_MB = 10

DISEASE_METADATA = {
    "ACNE": {
        "id": "acne", "name": "Mụn trứng cá", "latinName": "Acne vulgaris",
        "icd": "L70", "urgency": "low",
        "description": "Tình trạng nang lông bị bít tắc gây mụn đầu đen, đầu trắng hoặc tổn thương viêm.",
        "recommendation": "Chăm sóc da dịu nhẹ và khám da liễu nếu viêm kéo dài.",
    },
    "AK": {
        "id": "actinic_keratosis", "name": "Dày sừng ánh sáng", "latinName": "Actinic keratosis",
        "icd": "L57.0", "urgency": "medium",
        "description": "Tổn thương da tiền ung thư liên quan đến phơi nhiễm tia UV kéo dài.",
        "recommendation": "Nên khám bác sĩ da liễu để đánh giá và điều trị sớm.",
    },
    "BCC": {
        "id": "basal_cell_carcinoma", "name": "Ung thư biểu mô tế bào đáy", "latinName": "Basal cell carcinoma",
        "icd": "C44", "urgency": "high",
        "description": "Loại ung thư da thường tiến triển chậm nhưng có thể xâm lấn mô xung quanh.",
        "recommendation": "Cần khám chuyên khoa da liễu sớm.",
    },
    "BKL": {
        "id": "benign_keratosis", "name": "Dày sừng lành tính", "latinName": "Benign keratosis-like lesion",
        "icd": "L82", "urgency": "low",
        "description": "Nhóm tổn thương tăng sừng thường lành tính, gồm dày sừng tiết bã và lentigo.",
        "recommendation": "Theo dõi thay đổi kích thước, màu sắc hoặc hình dạng.",
    },
    "ECZEMA": {
        "id": "eczema", "name": "Chàm da", "latinName": "Eczema",
        "icd": "L30", "urgency": "low",
        "description": "Tình trạng viêm da gây đỏ, ngứa, khô hoặc bong tróc.",
        "recommendation": "Dưỡng ẩm và khám nếu triệu chứng dai dẳng hoặc lan rộng.",
    },
    "MELANOMA": {
        "id": "melanoma", "name": "U hắc tố ác tính", "latinName": "Malignant melanoma",
        "icd": "C43", "urgency": "high",
        "description": "Ung thư da ác tính phát triển từ tế bào sắc tố và có nguy cơ di căn.",
        "recommendation": "Cần khám chuyên khoa khẩn trương để đánh giá trực tiếp.",
    },
    "NEVUS": {
        "id": "nevus", "name": "Nốt ruồi", "latinName": "Melanocytic nevus",
        "icd": "D22", "urgency": "low",
        "description": "Tổn thương sắc tố thường lành tính hình thành từ tế bào hắc tố.",
        "recommendation": "Theo dõi quy tắc ABCDE và khám nếu có thay đổi bất thường.",
    },
    "PSORIASIS": {
        "id": "psoriasis", "name": "Vảy nến", "latinName": "Psoriasis",
        "icd": "L40", "urgency": "medium",
        "description": "Bệnh viêm da mạn tính tạo mảng đỏ, giới hạn rõ và phủ vảy.",
        "recommendation": "Nên khám da liễu để xác định mức độ và kế hoạch điều trị.",
    },
    "SCC": {
        "id": "squamous_cell_carcinoma", "name": "Ung thư biểu mô tế bào vảy", "latinName": "Squamous cell carcinoma",
        "icd": "C44", "urgency": "high",
        "description": "Ung thư da xuất phát từ tế bào vảy, có khả năng xâm lấn và di căn.",
        "recommendation": "Cần khám chuyên khoa sớm.",
    },
    "TINEA": {
        "id": "tinea", "name": "Nấm da", "latinName": "Dermatophytosis",
        "icd": "B35", "urgency": "low",
        "description": "Nhiễm nấm bề mặt da thường gây tổn thương dạng vòng, đỏ và ngứa.",
        "recommendation": "Giữ vùng da khô sạch và khám để lựa chọn thuốc kháng nấm phù hợp.",
    },
}


def _build_classification_response(data: dict) -> ClassificationDetail:
    candidates = []
    for item in data.get("candidates", []):
        label = item["label"]
        metadata = DISEASE_METADATA.get(label, {
            "id": label.lower(),
            "name": label,
            "latinName": label,
            "icd": "N/A",
            "urgency": "medium",
            "description": "Chua co thong tin mo ta cho nhan phan loai nay.",
            "recommendation": "Nen tham khao y kien bac si da lieu.",
        })
        candidates.append({
            **metadata,
            "confidence": round(item["confidence"] * 100, 1),
        })

    top_label = data["top_label"]
    top_metadata = DISEASE_METADATA.get(top_label, {
        "id": top_label.lower(),
        "name": top_label,
    })
    return ClassificationDetail(
        top_id=top_metadata["id"],
        top_label=top_metadata["name"],
        top_confidence=round(data["top_confidence"] * 100, 1),
        candidates=candidates,
    )


def _upload_bytes_to_minio(
    data: bytes,
    filename: str,
    folder: str,
    content_type: str = "image/png",
) -> str:
    """Upload raw bytes vào MinIO, trả về public URL."""
    _ensure_bucket()
    client = get_minio_client()
    object_name = _generate_object_name(filename, folder)

    client.put_object(
        bucket_name=settings.MINIO_BUCKET_NAME,
        object_name=object_name,
        data=io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )

    return get_file_url(object_name)


@router.get(
    "/history/{ai_result_id}",
    response_model=SkinAnalysisResponse,
    summary="Xem lai chi tiet mot ket qua phan tich",
)
def get_analysis_history_detail(
    ai_result_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_ai_result = (
        db.query(AIResult)
        .filter(
            AIResult.id == ai_result_id,
            AIResult.user_id == current_user.id,
        )
        .first()
    )
    if not db_ai_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay ket qua phan tich.",
        )

    db_validation = db_ai_result.input_validation
    if not db_validation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ket qua phan tich khong co du du lieu de hien thi lai.",
        )

    db_image = db_ai_result.image
    db_segmentation = db_ai_result.segmentation_result
    db_classification = db_ai_result.classification_result
    accepted = bool(db_validation.is_valid)
    confidence = float(db_validation.confidence or 0)
    issues = db_validation.issues or {}

    segmentation_response = None
    if db_segmentation:
        segmentation_response = SegmentationDetail(
            mask_url=db_segmentation.mask_url or "",
            roi_url=db_segmentation.roi_url or "",
            lesion_ratio=float(db_segmentation.lesion_area_percent or 0) / 100,
            bbox=[0, 0, 0, 0],
            fallback=False,
        )

    classification_response = None
    if db_classification and db_classification.top1_label:
        classification_response = _build_classification_response(
            {
                "top_label": db_classification.top1_label,
                "top_confidence": float(db_classification.top1_confidence or 0),
                "candidates": db_classification.topk or [],
            }
        )

    if accepted and db_segmentation:
        message = (
            "Anh hop le - phat hien ton thuong da "
            f"({float(db_segmentation.lesion_area_percent or 0):.1f}% dien tich)."
        )
    elif accepted:
        message = "Anh da nguoi hop le."
    else:
        message = "Anh khong dat dieu kien de phan tich."

    return SkinAnalysisResponse(
        accepted=accepted,
        message=message,
        original_image_url=db_image.image_url,
        validation=ValidationResult(
            is_skin=accepted,
            confidence=confidence,
            class_name=issues.get("class_name", "unknown"),
            probability=confidence,
            threshold=0.5,
        ),
        segmentation=segmentation_response,
        classification=classification_response,
        processing_time_ms=float(db_ai_result.processing_time_ms or 0),
        image_id=str(db_ai_result.image_id),
        ai_result_id=str(db_ai_result.id),
    )


@router.post(
    "/skin",
    response_model=SkinAnalysisResponse,
    summary="Phân tích ảnh da — Full Pipeline",
    description="""
    **Yêu cầu đăng nhập.**

    Upload ảnh da để phân tích qua AI pipeline:

    1. **Validate Skin** — Kiểm tra ảnh có phải da người không
    2. **Segmentation** — Khoanh vùng tổn thương (nếu hợp lệ)
    3. **Classification** — Phân loại ROI theo 10 nhóm bệnh da

    **Ảnh được lưu vào MinIO:**
    - Ảnh gốc: `skin-images/original/...`
    - Mask: `skin-images/masks/...`
    - ROI crop: `skin-images/roi/...`

    **Metadata lưu vào PostgreSQL:**
    - `images` — thông tin ảnh gốc
    - `ai_results` — kết quả pipeline
    - `input_validations` — kết quả validate
    - `segmentation_results` — kết quả segmentation
    - `classification_results` — top-1 và top-5 phân loại
    """,
)
async def analyze_skin(
    file: UploadFile = File(..., description="File ảnh da cần phân tích"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pipeline_start = time.time()

    # ── 1. Validate file ─────────────────────────────────────────
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Chỉ chấp nhận file ảnh ({', '.join(ALLOWED_CONTENT_TYPES)}). Nhận được: {file.content_type}",
        )

    image_bytes = await file.read()
    file_size_mb = len(image_bytes) / (1024 * 1024)

    if file_size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File quá lớn ({file_size_mb:.1f}MB). Tối đa: {MAX_FILE_SIZE_MB}MB",
        )

    # ── 2. Lưu ảnh gốc vào MinIO ────────────────────────────────
    original_url = _upload_bytes_to_minio(
        data=image_bytes,
        filename=file.filename or "image.jpg",
        folder="skin-images/original",
        content_type=file.content_type or "image/jpeg",
    )

    logger.info(f"📸 Original saved: {original_url} (user={current_user.id})")

    # ── 3. Lưu Image record vào DB ───────────────────────────────
    db_image = Image(
        user_id=current_user.id,
        image_url=original_url,
        file_size=len(image_bytes),
    )
    db.add(db_image)
    db.flush()  # Lấy ID mà chưa commit

    # ── 4. Gọi AI Service ────────────────────────────────────────
    try:
        ai_result = await call_ai_analyze(
            image_bytes=image_bytes,
            filename=file.filename or "image.jpg",
            content_type=file.content_type or "image/jpeg",
        )
    except AIServiceError as e:
        # Lưu lỗi vào DB
        db_ai_result = AIResult(
            user_id=current_user.id,
            image_id=db_image.id,
            status="error",
            error_message=e.detail,
            processing_time_ms=int((time.time() - pipeline_start) * 1000),
        )
        db.add(db_ai_result)
        db.commit()

        raise HTTPException(status_code=e.status_code, detail=e.detail)

    # ── 5. Parse AI response ─────────────────────────────────────
    accepted = ai_result.get("accepted", False)
    validation_data = ai_result.get("validation", {})
    seg_data = ai_result.get("segmentation")
    classification_data = ai_result.get("classification")
    ai_processing_ms = ai_result.get("processing_time_ms", 0)

    # ── 6. Tạo AI Result record ──────────────────────────────────
    total_ms = int((time.time() - pipeline_start) * 1000)

    db_ai_result = AIResult(
        user_id=current_user.id,
        image_id=db_image.id,
        model_version="skin_gate_v1 + seg_v2 + efficientnet_b0_clf",
        pipeline_version="1.1.0",
        status="completed" if accepted else "rejected",
        processing_time_ms=total_ms,
    )
    db.add(db_ai_result)
    db.flush()

    # ── 7. Lưu Input Validation ──────────────────────────────────
    db_validation = InputValidation(
        ai_result_id=db_ai_result.id,
        is_valid=validation_data.get("is_skin", False),
        confidence=validation_data.get("confidence", 0),
        issues={"class_name": validation_data.get("class_name", "unknown")},
    )
    db.add(db_validation)

    # ── 8. Xử lý Segmentation (nếu accepted) ────────────────────
    segmentation_response = None
    classification_response = None

    if accepted and seg_data:
        # Decode base64 → bytes → upload MinIO
        mask_b64 = seg_data.get("mask_base64", "")
        roi_b64 = seg_data.get("roi_base64", "")

        base_name = (file.filename or "image").rsplit(".", 1)[0]

        # Upload mask
        mask_url = None
        if mask_b64:
            mask_bytes = base64.b64decode(mask_b64)
            mask_url = _upload_bytes_to_minio(
                data=mask_bytes,
                filename=f"{base_name}_mask.png",
                folder="skin-images/masks",
                content_type="image/png",
            )

        # Upload ROI crop
        roi_url = None
        if roi_b64:
            roi_bytes = base64.b64decode(roi_b64)
            roi_url = _upload_bytes_to_minio(
                data=roi_bytes,
                filename=f"{base_name}_roi.png",
                folder="skin-images/roi",
                content_type="image/png",
            )

        logger.info(f"🎯 Segmentation saved: mask={mask_url}, roi={roi_url}")

        # Lưu DB
        db_seg = SegmentationResult(
            ai_result_id=db_ai_result.id,
            mask_url=mask_url,
            roi_url=roi_url,
            lesion_area_percent=seg_data.get("lesion_ratio", 0) * 100,
        )
        db.add(db_seg)

        segmentation_response = SegmentationDetail(
            mask_url=mask_url or "",
            roi_url=roi_url or "",
            lesion_ratio=seg_data.get("lesion_ratio", 0),
            bbox=seg_data.get("bbox", [0, 0, 0, 0]),
            fallback=seg_data.get("fallback", False),
        )

    if accepted and classification_data:
        classification_response = _build_classification_response(classification_data)
        db.add(DBClassificationResult(
            ai_result_id=db_ai_result.id,
            top1_label=classification_data.get("top_label"),
            top1_confidence=classification_data.get("top_confidence"),
            topk=classification_data.get("candidates", []),
        ))

    # ── 9. Commit DB ─────────────────────────────────────────────
    db.commit()

    logger.info(
        f"✅ Analysis complete: accepted={accepted}, "
        f"user={current_user.id}, time={total_ms}ms"
    )

    # ── 10. Trả response ─────────────────────────────────────────
    return SkinAnalysisResponse(
        accepted=accepted,
        message=ai_result.get("message", ""),
        original_image_url=original_url,
        validation=ValidationResult(
            is_skin=validation_data.get("is_skin", False),
            confidence=validation_data.get("confidence", 0),
            class_name=validation_data.get("class_name", "unknown"),
            probability=validation_data.get("probability", 0),
            threshold=validation_data.get("threshold", 0.5),
        ),
        segmentation=segmentation_response,
        classification=classification_response,
        processing_time_ms=round(total_ms, 1),
        image_id=str(db_image.id),
        ai_result_id=str(db_ai_result.id),
    )


@router.get(
    "/health",
    response_model=AIHealthResponse,
    summary="Kiểm tra trạng thái AI Service",
)
async def analyze_health():
    """Kiểm tra kết nối Backend → AI Service."""
    ai_health = await check_ai_health()
    return AIHealthResponse(
        backend_status="ok",
        ai_service=ai_health,
    )


from app.services.ai_service import call_ai_validate_skin, call_ai_segment

@router.post(
    "/validate-skin",
    summary="Kiểm tra ảnh có phải da người không (Gọi trực tiếp AI Model)",
)
async def validate_skin_only(
    file: UploadFile = File(...),
):
    """
    Endpoint này bọc (proxy) model `skin_validation` từ AI Service.
    Dùng để test model validate độc lập.
    """
    image_bytes = await file.read()
    try:
        result = await call_ai_validate_skin(
            image_bytes=image_bytes,
            filename=file.filename or "image.jpg",
            content_type=file.content_type or "image/jpeg"
        )
        return result
    except AIServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.post(
    "/segmentation",
    summary="Khoanh vùng tổn thương da (Gọi trực tiếp AI Model)",
)
async def segment_only(
    file: UploadFile = File(...),
):
    """
    Endpoint này bọc (proxy) model `segmentation` từ AI Service.
    Dùng để test model segmentation độc lập.
    """
    image_bytes = await file.read()
    try:
        result = await call_ai_segment(
            image_bytes=image_bytes,
            filename=file.filename or "image.jpg",
            content_type=file.content_type or "image/jpeg"
        )
        return result
    except AIServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.post(
    "/classification",
    response_model=ClassificationDetail,
    summary="Phân loại bệnh da 10 lớp (gọi trực tiếp AI Model)",
)
async def classify_only(
    file: UploadFile = File(...),
):
    """Proxy endpoint for testing the classifier independently in Swagger."""
    image_bytes = await file.read()
    try:
        result = await call_ai_classify(
            image_bytes=image_bytes,
            filename=file.filename or "image.jpg",
            content_type=file.content_type or "image/jpeg",
        )
        return _build_classification_response(result)
    except AIServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
