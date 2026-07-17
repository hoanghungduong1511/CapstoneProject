"""
MinIO Service — Upload, xoá, và lấy URL ảnh từ MinIO Object Storage.
"""

import io
import uuid
from datetime import datetime
from typing import Optional

from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error

from app.core.config import settings

# ── Singleton MinIO client ───────────────────────────────────────────
_client: Optional[Minio] = None


def get_minio_client() -> Minio:
    """Trả về singleton MinIO client, tạo lần đầu nếu chưa có."""
    global _client
    if _client is None:
        _client = Minio(
            endpoint=settings.MINIO_URL,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
    return _client


def _ensure_bucket() -> None:
    """Đảm bảo bucket đã tồn tại (phòng trường hợp init container chưa chạy)."""
    client = get_minio_client()
    if not client.bucket_exists(settings.MINIO_BUCKET_NAME):
        client.make_bucket(settings.MINIO_BUCKET_NAME)


def _generate_object_name(original_filename: str, folder: str = "") -> str:
    """
    Tạo tên file unique để tránh trùng lặp trên storage.
    Ví dụ: 'uploads/2026/04/02/a1b2c3d4_image.jpg'
    """
    now = datetime.utcnow()
    date_path = now.strftime("%Y/%m/%d")
    unique_id = uuid.uuid4().hex[:8]
    safe_name = original_filename.replace(" ", "_")

    prefix = f"{folder}/" if folder else "uploads/"
    return f"{prefix}{date_path}/{unique_id}_{safe_name}"


async def upload_file(
    file: UploadFile,
    folder: str = "",
) -> str:
    """
    Upload file lên MinIO và trả về URL public của file.

    Args:
        file: FastAPI UploadFile object.
        folder: Thư mục con trong bucket (mặc định: 'uploads').

    Returns:
        URL public để truy cập file, ví dụ:
        http://localhost:9000/skin-diseases-images/uploads/2026/04/02/a1b2c3d4_image.jpg
    """
    _ensure_bucket()
    client = get_minio_client()

    # Đọc toàn bộ nội dung file
    file_data = await file.read()
    file_size = len(file_data)
    content_type = file.content_type or "application/octet-stream"

    object_name = _generate_object_name(file.filename or "unknown", folder)

    client.put_object(
        bucket_name=settings.MINIO_BUCKET_NAME,
        object_name=object_name,
        data=io.BytesIO(file_data),
        length=file_size,
        content_type=content_type,
    )

    return get_file_url(object_name)


def delete_file(object_name: str) -> bool:
    """
    Xoá file khỏi MinIO bucket.

    Args:
        object_name: Đường dẫn object trong bucket (phần sau bucket name trong URL).

    Returns:
        True nếu xoá thành công, False nếu lỗi.
    """
    try:
        client = get_minio_client()
        client.remove_object(settings.MINIO_BUCKET_NAME, object_name)
        return True
    except S3Error:
        return False


def get_file_url(object_name: str) -> str:
    """
    Tạo URL public cho file đã upload.
    Vì bucket đã được set policy 'download' (public read),
    ta chỉ cần ghép URL thủ công mà không cần presigned URL.

    Args:
        object_name: Đường dẫn object trong bucket.

    Returns:
        URL dạng: http(s)://<minio_url>/<bucket>/<object_name>
    """
    scheme = "https" if settings.MINIO_SECURE else "http"
    return f"{scheme}://{settings.MINIO_URL}/{settings.MINIO_BUCKET_NAME}/{object_name}"


def extract_object_name(file_url: str) -> str:
    """
    Trích xuất object_name từ URL public (để dùng khi cần xoá file).

    Ví dụ:
        Input:  http://localhost:9000/skin-diseases-images/uploads/2026/04/02/abc_img.jpg
        Output: uploads/2026/04/02/abc_img.jpg
    """
    # Tìm vị trí bucket name trong URL rồi lấy phần sau nó
    bucket_prefix = f"{settings.MINIO_BUCKET_NAME}/"
    idx = file_url.find(bucket_prefix)
    if idx == -1:
        return file_url  # Fallback: trả về nguyên URL nếu không tìm thấy
    return file_url[idx + len(bucket_prefix):]
