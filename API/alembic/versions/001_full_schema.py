"""Full schema - 12 tables from dbdiagram

Revision ID: 001_full_schema
Revises:
Create Date: 2026-04-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_full_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. users ─────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False, server_default="local"),
        sa.Column("provider_id", sa.String(255), nullable=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="user"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── 2. images ────────────────────────────────────────────────────
    op.create_table(
        "images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("image_url", sa.String(500), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_images_user_id", "images", ["user_id"])

    # ── 3. ai_results ────────────────────────────────────────────────
    op.create_table(
        "ai_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("image_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("images.id"), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=True),
        sa.Column("pipeline_version", sa.String(100), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_ai_results_user_id", "ai_results", ["user_id"])
    op.create_index("ix_ai_results_image_id", "ai_results", ["image_id"])

    # ── 4. classification_results ────────────────────────────────────
    op.create_table(
        "classification_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ai_result_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_results.id"), nullable=False),
        sa.Column("top1_label", sa.String(255), nullable=True),
        sa.Column("top1_confidence", sa.Float(), nullable=True),
        sa.Column("topk", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_classification_results_ai_result_id", "classification_results", ["ai_result_id"])

    # ── 5. segmentation_results ──────────────────────────────────────
    op.create_table(
        "segmentation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ai_result_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_results.id"), nullable=False),
        sa.Column("mask_url", sa.String(500), nullable=True),
        sa.Column("lesion_area_percent", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_segmentation_results_ai_result_id", "segmentation_results", ["ai_result_id"])

    # ── 6. medical_contexts ──────────────────────────────────────────
    op.create_table(
        "medical_contexts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ai_result_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_results.id"), nullable=False),
        sa.Column("context_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_medical_contexts_ai_result_id", "medical_contexts", ["ai_result_id"])

    # ── 7. input_validations ─────────────────────────────────────────
    op.create_table(
        "input_validations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ai_result_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_results.id"), nullable=False),
        sa.Column("is_valid", sa.Boolean(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("issues", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_input_validations_ai_result_id", "input_validations", ["ai_result_id"])

    # ── 8. ai_features ───────────────────────────────────────────────
    op.create_table(
        "ai_features",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ai_result_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_results.id"), nullable=False),
        sa.Column("severity", sa.String(50), nullable=True),
        sa.Column("feature_vector", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_ai_features_ai_result_id", "ai_features", ["ai_result_id"])

    # ── 9. chat_sessions ─────────────────────────────────────────────
    op.create_table(
        "chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("ai_result_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_results.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])
    op.create_index("ix_chat_sessions_ai_result_id", "chat_sessions", ["ai_result_id"])

    # ── 10. chat_messages ────────────────────────────────────────────
    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_sessions.id"), nullable=False),
        sa.Column("role", sa.String(50), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])

    # ── 11. rag_queries ──────────────────────────────────────────────
    op.create_table(
        "rag_queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("medical_context_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("medical_contexts.id"), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_rag_queries_medical_context_id", "rag_queries", ["medical_context_id"])

    # ── 12. rag_results ──────────────────────────────────────────────
    op.create_table(
        "rag_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rag_query_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rag_queries.id"), nullable=False),
        sa.Column("document_id", sa.String(255), nullable=True),
        sa.Column("document_snippet", sa.Text(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_rag_results_rag_query_id", "rag_results", ["rag_query_id"])


def downgrade() -> None:
    # Drop tables in reverse order (respect FK dependencies)
    op.drop_table("rag_results")
    op.drop_table("rag_queries")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("ai_features")
    op.drop_table("input_validations")
    op.drop_table("medical_contexts")
    op.drop_table("segmentation_results")
    op.drop_table("classification_results")
    op.drop_table("ai_results")
    op.drop_table("images")
    op.drop_table("users")
