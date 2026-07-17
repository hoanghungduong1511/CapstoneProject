"""Add chatbot trace fields and disease knowledge.

Revision ID: a17c9d4e2f10
Revises: d93c3d7b895b
Create Date: 2026-06-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a17c9d4e2f10"
down_revision: Union[str, None] = "d93c3d7b895b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chat_sessions", sa.Column("title", sa.String(255), nullable=True))
    op.add_column(
        "chat_sessions",
        sa.Column("status", sa.String(50), server_default="active", nullable=False),
    )
    op.add_column(
        "chat_sessions",
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    for name, column in [
        ("ai_result_id", sa.Column("ai_result_id", postgresql.UUID(as_uuid=True))),
        (
            "medical_context_id",
            sa.Column("medical_context_id", postgresql.UUID(as_uuid=True)),
        ),
        ("rag_query_id", sa.Column("rag_query_id", postgresql.UUID(as_uuid=True))),
        ("rag_result_id", sa.Column("rag_result_id", postgresql.UUID(as_uuid=True))),
        ("safety_level", sa.Column("safety_level", sa.String(50))),
        ("model_name", sa.Column("model_name", sa.String(100))),
    ]:
        op.add_column("chat_messages", column)
    op.create_foreign_key(
        "fk_chat_messages_ai_result",
        "chat_messages",
        "ai_results",
        ["ai_result_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_chat_messages_medical_context",
        "chat_messages",
        "medical_contexts",
        ["medical_context_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_chat_messages_rag_query",
        "chat_messages",
        "rag_queries",
        ["rag_query_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_chat_messages_rag_result",
        "chat_messages",
        "rag_results",
        ["rag_result_id"],
        ["id"],
    )

    op.add_column(
        "medical_contexts",
        sa.Column("image_valid", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "medical_contexts",
        sa.Column("classification_topk_json", postgresql.JSONB()),
    )
    op.add_column(
        "medical_contexts",
        sa.Column("segmentation_summary_json", postgresql.JSONB()),
    )
    op.add_column(
        "medical_contexts", sa.Column("ai_features_json", postgresql.JSONB())
    )
    op.add_column(
        "medical_contexts", sa.Column("user_symptoms_json", postgresql.JSONB())
    )
    op.add_column(
        "medical_contexts", sa.Column("risk_summary", sa.String(255))
    )
    op.add_column(
        "medical_contexts",
        sa.Column("missing_questions_json", postgresql.JSONB()),
    )
    op.add_column(
        "medical_contexts",
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_unique_constraint(
        "uq_medical_contexts_ai_result_id", "medical_contexts", ["ai_result_id"]
    )

    op.add_column(
        "rag_queries", sa.Column("session_id", postgresql.UUID(as_uuid=True))
    )
    op.add_column("rag_queries", sa.Column("user_question", sa.Text()))
    op.add_column("rag_queries", sa.Column("rewritten_query", sa.Text()))
    op.add_column(
        "rag_queries", sa.Column("topk_labels_json", postgresql.JSONB())
    )
    op.create_foreign_key(
        "fk_rag_queries_session",
        "rag_queries",
        "chat_sessions",
        ["session_id"],
        ["id"],
    )

    op.add_column(
        "rag_results", sa.Column("retrieved_chunks_json", postgresql.JSONB())
    )
    op.add_column("rag_results", sa.Column("sources_json", postgresql.JSONB()))
    op.add_column(
        "rag_results", sa.Column("ranking_scores_json", postgresql.JSONB())
    )
    op.add_column("rag_results", sa.Column("final_context", sa.Text()))

    op.create_table(
        "disease_knowledge",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("label_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("label", sa.String(50), nullable=False, unique=True),
        sa.Column("name_vi", sa.String(255), nullable=False),
        sa.Column("name_en", sa.String(255), nullable=False),
        sa.Column("icd10", sa.String(50)),
        sa.Column("aliases", postgresql.JSONB()),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("common_signs", postgresql.JSONB()),
        sa.Column("common_symptoms", postgresql.JSONB()),
        sa.Column("risk_factors", postgresql.JSONB()),
        sa.Column("contagious", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("self_care", postgresql.JSONB()),
        sa.Column("avoid", postgresql.JSONB()),
        sa.Column("red_flags", postgresql.JSONB()),
        sa.Column("when_to_see_doctor", sa.Text()),
        sa.Column("urgency_level", sa.String(50), server_default="low", nullable=False),
        sa.Column("sources", postgresql.JSONB()),
        sa.Column("medical_review_date", sa.Date()),
        sa.Column("embedding", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_disease_knowledge_label", "disease_knowledge", ["label"])


def downgrade() -> None:
    op.drop_index("ix_disease_knowledge_label", table_name="disease_knowledge")
    op.drop_table("disease_knowledge")

    for column in [
        "final_context",
        "ranking_scores_json",
        "sources_json",
        "retrieved_chunks_json",
    ]:
        op.drop_column("rag_results", column)

    op.drop_constraint("fk_rag_queries_session", "rag_queries", type_="foreignkey")
    for column in ["topk_labels_json", "rewritten_query", "user_question", "session_id"]:
        op.drop_column("rag_queries", column)

    op.drop_constraint(
        "uq_medical_contexts_ai_result_id", "medical_contexts", type_="unique"
    )
    for column in [
        "updated_at",
        "missing_questions_json",
        "risk_summary",
        "user_symptoms_json",
        "ai_features_json",
        "segmentation_summary_json",
        "classification_topk_json",
        "image_valid",
    ]:
        op.drop_column("medical_contexts", column)

    for constraint in [
        "fk_chat_messages_rag_result",
        "fk_chat_messages_rag_query",
        "fk_chat_messages_medical_context",
        "fk_chat_messages_ai_result",
    ]:
        op.drop_constraint(constraint, "chat_messages", type_="foreignkey")
    for column in [
        "model_name",
        "safety_level",
        "rag_result_id",
        "rag_query_id",
        "medical_context_id",
        "ai_result_id",
    ]:
        op.drop_column("chat_messages", column)

    for column in ["updated_at", "status", "title"]:
        op.drop_column("chat_sessions", column)
