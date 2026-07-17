"""
Model: classification_results
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class ClassificationResult(Base):
    __tablename__ = "classification_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_result_id = Column(UUID(as_uuid=True), ForeignKey("ai_results.id"), nullable=False, index=True)
    top1_label = Column(String(255), nullable=True)
    top1_confidence = Column(Float, nullable=True)
    topk = Column(JSONB, nullable=True)  # JSON array of top-k predictions

    # ── Timestamps ───────────────────────────────────────────────────
    created_at = Column(DateTime, default=datetime.utcnow)

    # ── Relationships ────────────────────────────────────────────────
    ai_result = relationship("AIResult", back_populates="classification_result")

    def __repr__(self) -> str:
        return f"<ClassificationResult(id={self.id}, top1='{self.top1_label}')>"
