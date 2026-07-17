"""
Model: chat_messages
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = Column(String(50), nullable=True)  # "user" | "assistant" | "system"
    content = Column(Text, nullable=True)
    meta = Column("metadata", JSONB, nullable=True)
    ai_result_id = Column(UUID(as_uuid=True), ForeignKey("ai_results.id"), nullable=True)
    medical_context_id = Column(
        UUID(as_uuid=True), ForeignKey("medical_contexts.id"), nullable=True
    )
    rag_query_id = Column(UUID(as_uuid=True), ForeignKey("rag_queries.id"), nullable=True)
    rag_result_id = Column(UUID(as_uuid=True), ForeignKey("rag_results.id"), nullable=True)
    safety_level = Column(String(50), nullable=True)
    model_name = Column(String(100), nullable=True)

    # ── Timestamps ───────────────────────────────────────────────────
    created_at = Column(DateTime, default=datetime.utcnow)

    # ── Relationships ────────────────────────────────────────────────
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, role='{self.role}')>"
