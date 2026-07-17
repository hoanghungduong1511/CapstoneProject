"""
Model: medical_contexts
"""
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class MedicalContext(Base):
    __tablename__ = "medical_contexts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_result_id = Column(UUID(as_uuid=True), ForeignKey("ai_results.id"), nullable=False, index=True)
    context_json = Column(JSONB, nullable=True)
    image_valid = Column(sa.Boolean, nullable=False, default=True)
    classification_topk_json = Column(JSONB, nullable=True)
    segmentation_summary_json = Column(JSONB, nullable=True)
    ai_features_json = Column(JSONB, nullable=True)
    user_symptoms_json = Column(JSONB, nullable=True)
    risk_summary = Column(sa.String(255), nullable=True)
    missing_questions_json = Column(JSONB, nullable=True)

    # ── Timestamps ───────────────────────────────────────────────────
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── Relationships ────────────────────────────────────────────────
    ai_result = relationship("AIResult", back_populates="medical_context")
    rag_queries = relationship("RAGQuery", back_populates="medical_context")

    def __repr__(self) -> str:
        return f"<MedicalContext(id={self.id}, ai_result_id={self.ai_result_id})>"
