from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.schemas.responses import PipelineClassification
from app.services.model_manager import model_manager


router = APIRouter(prefix="/classify", tags=["Classification"])


@router.post("", response_model=PipelineClassification)
async def classify_skin_disease(file: UploadFile = File(...)):
    if file.content_type not in settings.ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="File ảnh không hợp lệ")

    image_bytes = await file.read()
    if len(image_bytes) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File ảnh vượt quá giới hạn")
    if model_manager.classification is None:
        raise HTTPException(status_code=503, detail="Classification model chưa sẵn sàng")

    try:
        return model_manager.classification.predict(image_bytes, top_k=5)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Classification failed: {exc}") from exc
