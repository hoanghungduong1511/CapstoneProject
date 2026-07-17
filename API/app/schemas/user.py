from datetime import date, datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel


# ── Request schemas ──────────────────────────────────────────────────
class UserUpdate(BaseModel):
    """Cập nhật thông tin cá nhân."""
    name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None  # "male" | "female" | "other"


# ── Response schemas ─────────────────────────────────────────────────
class AvatarResponse(BaseModel):
    avatar_url: str


class DiagnosisHistoryItem(BaseModel):
    """Một bản ghi lịch sử phân tích."""
    id: UUID
    image_url: Optional[str] = None
    top1_label: Optional[str] = None
    top1_confidence: Optional[float] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class DiagnosisHistoryResponse(BaseModel):
    items: List[DiagnosisHistoryItem]
    total: int
