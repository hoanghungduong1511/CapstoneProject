"""
Model: segmentation_results
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class SegmentationResult(Base):
    __tablename__ = "segmentation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_result_id = Column(UUID(as_uuid=True), ForeignKey("ai_results.id"), nullable=False, index=True)
    mask_url = Column(String(500), nullable=True)
    roi_url = Column(String(500), nullable=True)
    lesion_area_percent = Column(Float, nullable=True)

    # ── Timestamps ───────────────────────────────────────────────────
    created_at = Column(DateTime, default=datetime.utcnow)

    # ── Relationships ────────────────────────────────────────────────
    ai_result = relationship("AIResult", back_populates="segmentation_result")

    def __repr__(self) -> str:
        return f"<SegmentationResult(id={self.id}, lesion_area={self.lesion_area_percent})>"
