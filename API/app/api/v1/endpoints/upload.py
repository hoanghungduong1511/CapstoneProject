"""
Upload API — Endpoint test upload/xoá ảnh với MinIO.
"""

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from app.services.minio_service import (
    delete_file,
    extract_object_name,
    upload_file,
)

router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("/image")
async def upload_image(file: UploadFile = File(...)):
    """
    Upload một ảnh lên MinIO.

    - Chấp nhận file ảnh (jpg, png, webp, ...)
    - Trả về URL public có thể truy cập trực tiếp từ trình duyệt.
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        return JSONResponse(
            status_code=400,
            content={"error": f"Chỉ chấp nhận file ảnh ({', '.join(allowed_types)})"},
        )

    url = await upload_file(file, folder="skin-images")
    return {
        "message": "Upload thành công ✅",
        "image_url": url,
    }


@router.delete("/image")
async def delete_image(image_url: str):
    """
    Xoá ảnh khỏi MinIO bằng URL đã nhận từ lúc upload.
    """
    object_name = extract_object_name(image_url)
    success = delete_file(object_name)

    if success:
        return {"message": "Xoá thành công ✅"}
    return JSONResponse(
        status_code=404,
        content={"error": "Không tìm thấy file hoặc xoá thất bại"},
    )
