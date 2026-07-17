"""
Model: ai_features
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class AIFeature(Base):
    __tablename__ = "ai_features"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_result_id = Column(UUID(as_uuid=True), ForeignKey("ai_results.id"), nullable=False, index=True)
    severity = Column(String(50), nullable=True)
    feature_vector = Column(JSONB, nullable=True)

    # ── Timestamps ───────────────────────────────────────────────────
    created_at = Column(DateTime, default=datetime.utcnow)

    # ── Relationships ────────────────────────────────────────────────
    ai_result = relationship("AIResult", back_populates="ai_feature")

    def __repr__(self) -> str:
        return f"<AIFeature(id={self.id}, severity='{self.severity}')>"
