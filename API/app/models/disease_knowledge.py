"""Normalized medical knowledge used by the chatbot RAG layer."""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


class DiseaseKnowledge(Base):
    __tablename__ = "disease_knowledge"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    label_id = Column(Integer, nullable=False, unique=True)
    label = Column(String(50), nullable=False, unique=True, index=True)
    name_vi = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=False)
    icd10 = Column(String(50), nullable=True)
    aliases = Column(JSONB, nullable=True)
    summary = Column(Text, nullable=False)
    common_signs = Column(JSONB, nullable=True)
    common_symptoms = Column(JSONB, nullable=True)
    risk_factors = Column(JSONB, nullable=True)
    contagious = Column(Boolean, nullable=False, default=False)
    self_care = Column(JSONB, nullable=True)
    avoid = Column(JSONB, nullable=True)
    red_flags = Column(JSONB, nullable=True)
    when_to_see_doctor = Column(Text, nullable=True)
    urgency_level = Column(String(50), nullable=False, default="low")
    sources = Column(JSONB, nullable=True)
    medical_review_date = Column(Date, nullable=True, default=date.today)
    embedding = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
