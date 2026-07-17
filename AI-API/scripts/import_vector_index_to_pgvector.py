from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import local chatbot vector_index chunks/embeddings into PostgreSQL pgvector."
    )
    parser.add_argument(
        "--index-dir",
        type=Path,
        default=Path(settings.VECTOR_INDEX_DIR),
        help="Folder containing index_config.json, chunks.jsonl and embeddings.npy.",
    )
    parser.add_argument(
        "--database-url",
        default=(
            os.getenv("PGVECTOR_DATABASE_URL")
            or os.getenv("DATABASE_URL")
            or settings.PGVECTOR_DATABASE_URL
        ),
    )
    parser.add_argument("--table", default=settings.PGVECTOR_TABLE)
    parser.add_argument("--reset", action="store_true", help="Delete existing rows first.")
    return parser.parse_args()


def vector_literal(vector: np.ndarray) -> str:
    return "[" + ",".join(f"{float(value):.8f}" for value in vector) + "]"


def load_chunks(path: Path) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                chunks.append(json.loads(line))
    return chunks


def normalize_metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except json.JSONDecodeError:
            return {"raw": value}
    return {}


def main() -> None:
    args = parse_args()
    if not args.database_url:
        raise SystemExit("PGVECTOR_DATABASE_URL or DATABASE_URL is required.")

    config_path = args.index_dir / "index_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    chunks_path = args.index_dir / config["chunks_file"]
    embeddings_path = args.index_dir / config["embeddings_file"]

    chunks = load_chunks(chunks_path)
    embeddings = np.load(embeddings_path).astype(np.float32)
    if embeddings.shape[0] != len(chunks):
        raise SystemExit(
            f"Invalid index: {embeddings.shape[0]} embeddings for {len(chunks)} chunks."
        )

    dimension = int(embeddings.shape[1])

    try:
        import psycopg
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise SystemExit(
            "psycopg is not installed. Run `pip install -r requirements.txt`."
        ) from exc

    with psycopg.connect(args.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {args.table} (
                    id BIGSERIAL PRIMARY KEY,
                    chunk_id TEXT UNIQUE NOT NULL,
                    label_id INTEGER,
                    label TEXT NOT NULL,
                    disease_name TEXT,
                    name_en TEXT,
                    icd10 TEXT,
                    chunk_type TEXT NOT NULL,
                    chunk_title TEXT,
                    content TEXT NOT NULL,
                    source_url TEXT,
                    urgency_level TEXT,
                    medical_review_date TEXT,
                    metadata_json JSONB,
                    embedding vector({dimension}) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{args.table}_label_type ON {args.table} (label, chunk_type)"
            )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{args.table}_embedding_hnsw ON {args.table} USING hnsw (embedding vector_cosine_ops)"
            )
            if args.reset:
                cur.execute(f"DELETE FROM {args.table}")

            upsert_sql = f"""
                INSERT INTO {args.table} (
                    chunk_id, label_id, label, disease_name, name_en, icd10,
                    chunk_type, chunk_title, content, source_url, urgency_level,
                    medical_review_date, metadata_json, embedding
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector
                )
                ON CONFLICT (chunk_id) DO UPDATE SET
                    label_id = EXCLUDED.label_id,
                    label = EXCLUDED.label,
                    disease_name = EXCLUDED.disease_name,
                    name_en = EXCLUDED.name_en,
                    icd10 = EXCLUDED.icd10,
                    chunk_type = EXCLUDED.chunk_type,
                    chunk_title = EXCLUDED.chunk_title,
                    content = EXCLUDED.content,
                    source_url = EXCLUDED.source_url,
                    urgency_level = EXCLUDED.urgency_level,
                    medical_review_date = EXCLUDED.medical_review_date,
                    metadata_json = EXCLUDED.metadata_json,
                    embedding = EXCLUDED.embedding
            """
            for chunk, vector in zip(chunks, embeddings, strict=True):
                cur.execute(
                    upsert_sql,
                    (
                        str(chunk.get("chunk_id") or ""),
                        chunk.get("label_id"),
                        str(chunk.get("label") or "").upper(),
                        chunk.get("disease_name"),
                        chunk.get("name_en"),
                        chunk.get("icd10"),
                        str(chunk.get("chunk_type") or ""),
                        chunk.get("chunk_title"),
                        str(chunk.get("content") or ""),
                        chunk.get("source_url"),
                        chunk.get("urgency_level"),
                        chunk.get("medical_review_date"),
                        Jsonb(normalize_metadata(chunk.get("metadata_json"))),
                        vector_literal(vector),
                    ),
                )
        conn.commit()

    print(
        f"Imported {len(chunks)} chunks into {args.table} "
        f"with embedding dimension {dimension}."
    )


if __name__ == "__main__":
    main()
