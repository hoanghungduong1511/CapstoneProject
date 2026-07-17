"""
Model: input_validations
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class InputValidation(Base):
    __tablename__ = "input_validations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_result_id = Column(UUID(as_uuid=True), ForeignKey("ai_results.id"), nullable=False, index=True)
    is_valid = Column(Boolean, nullable=True)
    confidence = Column(Float, nullable=True)
    quality_score = Column(Float, nullable=True)
    issues = Column(JSONB, nullable=True)

    # ── Timestamps ───────────────────────────────────────────────────
    created_at = Column(DateTime, default=datetime.utcnow)

    # ── Relationships ────────────────────────────────────────────────
    ai_result = relationship("AIResult", back_populates="input_validation")

    def __repr__(self) -> str:
        return f"<InputValidation(id={self.id}, is_valid={self.is_valid})>"
