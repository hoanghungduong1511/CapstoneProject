from fastapi import APIRouter

from app.data.disease_catalog import list_disease_catalog
from app.schemas.chat import (
    ChatGenerateRequest,
    ChatGenerateResponse,
    DiseaseCatalogItem,
    MedicalChatRequest,
    MedicalChatResponse,
)
from app.services.chatbot_service import chatbot_service


router = APIRouter(prefix="/chat", tags=["Medical Chatbot"])


@router.get(
    "/catalog",
    response_model=list[DiseaseCatalogItem],
    summary="Danh sách metadata 10 lớp bệnh da",
)
def disease_catalog():
    return list_disease_catalog()


@router.post(
    "",
    response_model=MedicalChatResponse,
    summary="Tư vấn da liễu theo kết quả phân tích AI",
)
async def medical_chat(payload: MedicalChatRequest):
    return await chatbot_service.reply(payload)


@router.post(
    "/generate",
    response_model=ChatGenerateResponse,
    summary="Sinh câu trả lời RAG từ medical context đã chuẩn hóa",
)
async def generate_chat(payload: ChatGenerateRequest):
    return await chatbot_service.generate(payload)
