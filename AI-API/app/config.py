"""
AI Service — Configuration
Đọc settings từ environment variables, có giá trị mặc định hợp lý.
"""

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Thông tin chung ──────────────────────────────────────────────
    PROJECT_NAME: str = "SkinDiseases AI Service"
    API_V1_STR: str = "/api/v1"
    VERSION: str = "1.0.0"

    # ── Server ───────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    LOG_LEVEL: str = "info"

    # ── AI Models ────────────────────────────────────────────────────
    MODEL_DIR: str = str(Path(__file__).resolve().parent.parent / "ai_models")
    DEVICE: str = "auto"  # "auto", "cuda", "cpu"

    # Medical chatbot
    LLM_PROVIDER: str = "openai"  # "openai", "gemini", or "mock"
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4.1-mini"
    OPENAI_TIMEOUT_SECONDS: float = 30.0
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.5-flash"
    GEMINI_TIMEOUT_SECONDS: float = 120.0
    RAG_MODE: str = "csv"  # "csv", "vector", or "pgvector"
    RAG_TOP_K: int = 5
    RAG_MIN_SCORE: float = 0.05
    VECTOR_INDEX_DIR: str = str(
        Path(__file__).resolve().parent.parent
        / "data"
        / "processed"
        / "chatbot"
        / "vector_index_st"
    )
    CHATBOT_TEMPERATURE: float = 0.3
    CHATBOT_MAX_TOKENS: int = 800
    VECTOR_DB_ENABLED: bool = False
    PGVECTOR_DATABASE_URL: str | None = None
    PGVECTOR_TABLE: str = "disease_knowledge_chunks"
    PGVECTOR_EMBEDDING_PROVIDER: str = "sentence-transformers"
    PGVECTOR_EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    DISEASE_KNOWLEDGE_PATH: str = str(
        Path(__file__).resolve().parent.parent
        / "data"
        / "processed"
        / "chatbot"
        / "disease_knowledge.csv"
    )

    # ── Upload limits ────────────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_CONTENT_TYPES: List[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/bmp",
        "image/tiff",
    ]

    # ── CORS ─────────────────────────────────────────────────────────
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

settings = Settings()
