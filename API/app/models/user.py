"""
Model: users
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Date, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    provider = Column(String(50), nullable=False, default="local")  # "local" | "google"
    provider_id = Column(String(255), nullable=True)
    role = Column(String(50), nullable=False, default="user")
    status = Column(String(50), nullable=False, default="active")
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)

    # ── Timestamps ───────────────────────────────────────────────────
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # ── Relationships ────────────────────────────────────────────────
    images = relationship("Image", back_populates="user")
    ai_results = relationship("AIResult", back_populates="user")
    chat_sessions = relationship("ChatSession", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', provider='{self.provider}')>"
