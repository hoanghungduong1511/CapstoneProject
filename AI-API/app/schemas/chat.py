from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=10000)


class ChatCandidate(BaseModel):
    label: str
    confidence: float = Field(ge=0)


class ChatAnalysisContext(BaseModel):
    image_valid: bool = True
    validation_confidence: float | None = Field(default=None, ge=0)
    top_label: str | None = None
    top_confidence: float | None = Field(default=None, ge=0)
    candidates: list[ChatCandidate] = Field(default_factory=list, max_length=10)
    lesion_ratio: float | None = Field(default=None, ge=0)
    mask_available: bool = False
    ai_features: dict[str, Any] | None = None


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


class MedicalChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    analysis: ChatAnalysisContext | None = None
    patient: UserSymptoms | None = None
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=12)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be blank")
        return value


class ChatGenerateRequest(BaseModel):
    user_question: str = Field(min_length=1, max_length=4000)
    medical_context: dict[str, Any]
    chat_history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=12)


class RetrievedChunk(BaseModel):
    document_id: str
    label: str
    name_vi: str
    content: str
    score: float
    sources: list[str] = Field(default_factory=list)


class ChatGenerateResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    answer: str
    safety_level: Literal["low", "medium", "high", "urgent"]
    sources: list[str]
    missing_questions: list[str]
    retrieved_chunks: list[RetrievedChunk]
    rewritten_query: str
    model_name: str
    token_usage: dict[str, int] | None = None


class MedicalChatResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    message: str
    source: Literal["openai", "gemini", "mock", "safety_triage"]
    model: str
    normalized_label: str | None = None
    disease_name: str | None = None
    urgency: Literal["low", "medium", "high", "urgent", "unknown"] = "unknown"
    confidence_note: str | None = None
    disclaimer: str
    safety_level: Literal["low", "medium", "high", "urgent"] = "low"
    sources: list[str] = Field(default_factory=list)
    missing_questions: list[str] = Field(default_factory=list)


class DiseaseCatalogItem(BaseModel):
    label_id: int
    label: str
    name_vi: str
    name_en: str
    icd10: str
    urgency_level: Literal["low", "medium", "high", "emergency"]
