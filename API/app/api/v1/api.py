from fastapi import APIRouter

from app.api.v1.endpoints import admin, analyze, auth, chat, upload

api_router = APIRouter()

# Gom tất cả endpoint routers tại đây
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(upload.router)
api_router.include_router(analyze.router)
api_router.include_router(chat.router)
