"""
Model: ai_results
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class AIResult(Base):
    __tablename__ = "ai_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    image_id = Column(UUID(as_uuid=True), ForeignKey("images.id"), nullable=False, index=True)
    model_version = Column(String(100), nullable=True)
    pipeline_version = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)

    # ── Timestamps ───────────────────────────────────────────────────
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── Relationships ────────────────────────────────────────────────
    user = relationship("User", back_populates="ai_results")
    image = relationship("Image", back_populates="ai_results")
    classification_result = relationship("ClassificationResult", back_populates="ai_result", uselist=False)
    segmentation_result = relationship("SegmentationResult", back_populates="ai_result", uselist=False)
    medical_context = relationship("MedicalContext", back_populates="ai_result", uselist=False)
    input_validation = relationship("InputValidation", back_populates="ai_result", uselist=False)
    ai_feature = relationship("AIFeature", back_populates="ai_result", uselist=False)
    chat_sessions = relationship("ChatSession", back_populates="ai_result")

    def __repr__(self) -> str:
        return f"<AIResult(id={self.id}, status='{self.status}')>"
