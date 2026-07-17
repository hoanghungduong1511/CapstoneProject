"""
SkinDiseases AI Service — FastAPI Application
==============================================
Microservice riêng biệt cho AI inference.
Load models 1 lần khi startup, serve predictions qua REST API.

Chạy local:
    uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

Docker:
    docker compose up ai-service
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.api.v1.endpoints import health
from app.config import settings
from app.services.model_manager import model_manager

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan: load models khi startup ────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load AI models khi server khởi động, cleanup khi tắt."""
    logger.info("=" * 60)
    logger.info(f"  🚀 {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"  📁 Model dir: {settings.MODEL_DIR}")
    logger.info("=" * 60)

    # Load tất cả models
    model_manager.load_models(
        model_dir=settings.MODEL_DIR,
        device=settings.DEVICE,
    )

    health_info = model_manager.health_check()
    loaded_count = sum(
        1 for m in health_info["models"].values() if m["loaded"]
    )
    total_count = len(health_info["models"])
    logger.info(f"📊 Models loaded: {loaded_count}/{total_count} on {health_info['device']}")
    logger.info(f"🌐 Swagger UI: http://localhost:{settings.PORT}/docs")
    logger.info("=" * 60)

    yield  # Server đang chạy

    # Cleanup khi shutdown
    logger.info("🛑 Shutting down AI Service...")


# ── FastAPI App ──────────────────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="""
## 🩺 SkinDiseases AI Service

Microservice AI cho hệ thống hỗ trợ chẩn đoán bệnh da liễu.

### 📋 Models hiện có:

| Model | Architecture | Task |
|-------|-------------|------|
| **Skin Validation** | EfficientNet-B0 | Kiểm tra ảnh có phải da người |
| **Segmentation** | U-Net + EfficientNet-B3 | Khoanh vùng tổn thương da |

### 🔄 Pipeline:

```
Upload ảnh → Validate Skin → Segmentation → Kết quả
```

### 🔗 Tích hợp:

Service này được gọi bởi **SkinDiseases Backend API** (`skin_diseases_api:8000`)
thông qua Docker internal network.
    """,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────────────
# Health check (root level, không cần /api/v1 prefix)
app.include_router(health.router)

# AI endpoints (with /api/v1 prefix)
app.include_router(api_router, prefix=settings.API_V1_STR)


# ── Root endpoint ────────────────────────────────────────────────────
@app.get("/", tags=["🩺 Health Check"], summary="Root — Service info")
def root():
    """Kiểm tra nhanh service có hoạt động không."""
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
    }
