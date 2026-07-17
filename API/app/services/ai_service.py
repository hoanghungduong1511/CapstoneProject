"""
AI Service Client — Gọi AI Service microservice qua HTTP.
Backend API (:8000) → AI Service (:8001)
"""

import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Lỗi khi gọi AI Service."""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


async def call_ai_analyze(
    image_bytes: bytes,
    filename: str,
    content_type: str = "image/jpeg",
) -> dict:
    """
    Gọi AI Service full pipeline: validate skin → segmentation.

    Args:
        image_bytes: Raw bytes của ảnh.
        filename: Tên file gốc.
        content_type: MIME type (image/jpeg, image/png, ...).

    Returns:
        Dict chứa kết quả pipeline (accepted, validation, segmentation, ...).

    Raises:
        AIServiceError: Khi AI Service trả lỗi hoặc không available.
    """
    url = f"{settings.AI_SERVICE_URL}/api/v1/analyze"

    try:
        async with httpx.AsyncClient(timeout=settings.AI_SERVICE_TIMEOUT) as client:
            files = {"file": (filename, image_bytes, content_type)}
            response = await client.post(url, files=files)

        if response.status_code == 200:
            return response.json()

        # AI Service trả lỗi
        error_detail = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        logger.error(f"AI Service error {response.status_code}: {error_detail}")
        raise AIServiceError(
            status_code=response.status_code,
            detail=f"AI Service error: {error_detail}",
        )

    except httpx.ConnectError:
        logger.error(f"Cannot connect to AI Service at {settings.AI_SERVICE_URL}")
        raise AIServiceError(
            status_code=503,
            detail="AI Service không khả dụng. Vui lòng thử lại sau.",
        )
    except httpx.TimeoutException:
        logger.error(f"AI Service timeout after {settings.AI_SERVICE_TIMEOUT}s")
        raise AIServiceError(
            status_code=504,
            detail="AI Service xử lý quá lâu. Vui lòng thử lại.",
        )


async def call_ai_validate_skin(
    image_bytes: bytes,
    filename: str,
    content_type: str = "image/jpeg",
) -> dict:
    url = f"{settings.AI_SERVICE_URL}/api/v1/validate-skin"
    try:
        async with httpx.AsyncClient(timeout=settings.AI_SERVICE_TIMEOUT) as client:
            files = {"file": (filename, image_bytes, content_type)}
            response = await client.post(url, files=files)
        if response.status_code == 200:
            return response.json()
        error_detail = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        raise AIServiceError(status_code=response.status_code, detail=str(error_detail))
    except Exception as e:
        raise AIServiceError(status_code=503, detail=f"AI Service error: {str(e)}")


async def call_ai_segment(
    image_bytes: bytes,
    filename: str,
    content_type: str = "image/jpeg",
) -> dict:
    url = f"{settings.AI_SERVICE_URL}/api/v1/segment"
    try:
        async with httpx.AsyncClient(timeout=settings.AI_SERVICE_TIMEOUT) as client:
            files = {"file": (filename, image_bytes, content_type)}
            response = await client.post(url, files=files)
        if response.status_code == 200:
            return response.json()
        error_detail = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        raise AIServiceError(status_code=response.status_code, detail=str(error_detail))
    except Exception as e:
        raise AIServiceError(status_code=503, detail=f"AI Service error: {str(e)}")


async def call_ai_classify(
    image_bytes: bytes,
    filename: str,
    content_type: str = "image/jpeg",
) -> dict:
    """Call the standalone 10-class skin disease classifier."""
    url = f"{settings.AI_SERVICE_URL}/api/v1/classify"
    try:
        async with httpx.AsyncClient(timeout=settings.AI_SERVICE_TIMEOUT) as client:
            files = {"file": (filename, image_bytes, content_type)}
            response = await client.post(url, files=files)
        if response.status_code == 200:
            return response.json()
        error_detail = (
            response.json()
            if response.headers.get("content-type", "").startswith("application/json")
            else response.text
        )
        raise AIServiceError(
            status_code=response.status_code,
            detail=str(error_detail),
        )
    except AIServiceError:
        raise
    except httpx.ConnectError as exc:
        raise AIServiceError(
            status_code=503,
            detail="AI Service khong kha dung. Vui long thu lai sau.",
        ) from exc
    except httpx.TimeoutException as exc:
        raise AIServiceError(
            status_code=504,
            detail="Classification model xu ly qua lau. Vui long thu lai.",
        ) from exc


async def check_ai_health() -> Optional[dict]:
    """Kiểm tra health của AI Service."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{settings.AI_SERVICE_URL}/health")
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    return None


async def call_ai_chat(
    user_question: str,
    medical_context: dict,
    chat_history: list[dict],
) -> dict:
    """Call the AI service RAG/LLM endpoint with de-identified context."""
    url = f"{settings.AI_SERVICE_URL}/api/v1/chat/generate"
    payload = {
        "user_question": user_question,
        "medical_context": medical_context,
        "chat_history": chat_history,
    }
    try:
        async with httpx.AsyncClient(timeout=settings.AI_SERVICE_TIMEOUT) as client:
            response = await client.post(url, json=payload)
        if response.status_code == 200:
            return response.json()
        detail = (
            response.json()
            if response.headers.get("content-type", "").startswith("application/json")
            else response.text
        )
        raise AIServiceError(response.status_code, str(detail))
    except AIServiceError:
        raise
    except httpx.ConnectError as exc:
        raise AIServiceError(
            503, "AI chatbot service không khả dụng. Vui lòng thử lại sau."
        ) from exc
    except httpx.TimeoutException as exc:
        raise AIServiceError(
            504, "AI chatbot phản hồi quá lâu. Vui lòng thử lại."
        ) from exc
