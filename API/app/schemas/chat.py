from datetime import datetime
from typing import Any, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChatSessionCreate(BaseModel):
    ai_result_id: Optional[UUID] = None
    title: Optional[str] = Field(default=None, max_length=255)
    initial_message: Optional[str] = Field(default=None, max_length=10000)


class UserSymptoms(BaseModel):
    itch: bool | None = None
    hurt: bool | None = None
    bleed: bool | None = None
    ulcerated: bool | None = None
    changed: bool | None = None
    grew: bool | None = None
    elevation: bool | None = None
    duration: str | None = Field(default=None, max_length=200)
    body_site: str | None = Field(default=None, max_length=100)
    skin_cancer_history: bool | None = None


class ChatMessageCreate(BaseModel):
    # New generated-chat contract
    message: str | None = Field(default=None, min_length=1, max_length=4000)
    ai_result_id: UUID | None = None
    user_symptoms: UserSymptoms | None = None

    # Backward-compatible history-only contract
    role: Literal["user", "assistant"] | None = None
    content: str | None = Field(default=None, min_length=1, max_length=20000)
    metadata: Optional[dict] = None

    @model_validator(mode="after")
    def require_message_or_content(self):
        if not self.message and not self.content:
            raise ValueError("message hoặc content là bắt buộc")
        return self


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID
    role: str
    content: str
    metadata: Optional[dict] = Field(default=None, validation_alias="meta")
    ai_result_id: UUID | None = None
    medical_context_id: UUID | None = None
    rag_query_id: UUID | None = None
    rag_result_id: UUID | None = None
    safety_level: str | None = None
    model_name: str | None = None
    created_at: datetime

class ChatTurnResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    message_id: UUID
    answer: str
    safety_level: Literal["low", "medium", "high", "urgent"]
    sources: list[str]
    missing_questions: list[str]
    medical_context_id: UUID
    rag_query_id: UUID
    rag_result_id: UUID
    model_name: str
    token_usage: dict[str, int] | None = None


class ChatSessionSummary(BaseModel):
    id: UUID
    ai_result_id: Optional[UUID] = None
    title: str
    status: str
    message_count: int
    last_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime | None = None
    last_message_at: datetime


class ChatSessionListResponse(BaseModel):
    items: List[ChatSessionSummary]
    total: int


class ChatSessionDetail(BaseModel):
    id: UUID
    ai_result_id: Optional[UUID] = None
    title: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime | None = None
    messages: List[ChatMessageResponse]
