"""
Model: rag_results
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class RAGResult(Base):
    __tablename__ = "rag_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rag_query_id = Column(UUID(as_uuid=True), ForeignKey("rag_queries.id"), nullable=False, index=True)
    document_id = Column(String(255), nullable=True)
    document_snippet = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    retrieved_chunks_json = Column(JSONB, nullable=True)
    sources_json = Column(JSONB, nullable=True)
    ranking_scores_json = Column(JSONB, nullable=True)
    final_context = Column(Text, nullable=True)

    # ── Timestamps ───────────────────────────────────────────────────
    created_at = Column(DateTime, default=datetime.utcnow)

    # ── Relationships ────────────────────────────────────────────────
    rag_query = relationship("RAGQuery", back_populates="rag_results")

    def __repr__(self) -> str:
        return f"<RAGResult(id={self.id}, score={self.score})>"
