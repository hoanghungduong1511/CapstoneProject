"""
API v1 Router — Gom tất cả endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    chat,
    classification,
    health,
    pipeline,
    segmentation,
    skin_validation,
)

api_router = APIRouter()

# Health check (không có prefix /api/v1)
# → Được mount riêng ở main.py

# AI endpoints
api_router.include_router(skin_validation.router)
api_router.include_router(segmentation.router)
api_router.include_router(classification.router)
api_router.include_router(pipeline.router)
api_router.include_router(chat.router)
