"""
Model: rag_queries
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class RAGQuery(Base):
    __tablename__ = "rag_queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medical_context_id = Column(UUID(as_uuid=True), ForeignKey("medical_contexts.id"), nullable=False, index=True)
    query_text = Column(Text, nullable=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=True)
    user_question = Column(Text, nullable=True)
    rewritten_query = Column(Text, nullable=True)
    topk_labels_json = Column(JSONB, nullable=True)

    # ── Timestamps ───────────────────────────────────────────────────
    created_at = Column(DateTime, default=datetime.utcnow)

    # ── Relationships ────────────────────────────────────────────────
    medical_context = relationship("MedicalContext", back_populates="rag_queries")
    rag_results = relationship("RAGResult", back_populates="rag_query")

    def __repr__(self) -> str:
        return f"<RAGQuery(id={self.id})>"
