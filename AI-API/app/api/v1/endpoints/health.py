"""
Health Check Endpoint
Kiểm tra trạng thái service và tất cả AI models.
"""

from fastapi import APIRouter

from app.schemas.responses import HealthResponse
from app.services.model_manager import model_manager
from app.config import settings

router = APIRouter(tags=["🩺 Health Check"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Kiểm tra trạng thái AI Service",
    description="""
    Trả về trạng thái của service và tất cả AI models đã load.
    
    Dùng endpoint này để:
    - Kiểm tra service có hoạt động không
    - Kiểm tra từng model đã load thành công chưa
    - Xem device đang sử dụng (CUDA / CPU)
    """,
)
def health_check():
    health = model_manager.health_check()
    return HealthResponse(
        status="ok",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        device=health["device"],
        models=health["models"],
    )
