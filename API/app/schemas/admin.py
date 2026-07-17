from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class AdminUserListItem(BaseModel):
    id: UUID
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    provider: str
    status: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    analysis_count: int = 0
    last_analysis_at: Optional[datetime] = None
    created_at: datetime


class AdminUserListResponse(BaseModel):
    items: List[AdminUserListItem]
    total: int
    active: int
    inactive: int
    total_analyses: int


class AdminAnalysisHistoryItem(BaseModel):
    id: UUID
    image_url: Optional[str] = None
    status: str
    top1_label: Optional[str] = None
    top1_confidence: Optional[float] = None
    lesion_area_percent: Optional[float] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime


class AdminUserDetail(BaseModel):
    id: UUID
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    provider: str
    role: str
    status: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    analysis_count: int
    history: List[AdminAnalysisHistoryItem]


class AdminUserStatusUpdate(BaseModel):
    locked: bool


class AdminUserStatusResponse(BaseModel):
    id: UUID
    status: str
    message: str
