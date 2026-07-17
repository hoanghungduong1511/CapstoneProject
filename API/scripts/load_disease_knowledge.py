"""Upsert the curated disease knowledge CSV into PostgreSQL."""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import SessionLocal
from app.models.disease_knowledge import DiseaseKnowledge


LIST_FIELDS = {
    "aliases",
    "common_signs",
    "common_symptoms",
    "risk_factors",
    "self_care",
    "avoid",
    "red_flags",
}


def split_list(value: str | None, separator: str = ";") -> list[str]:
    return [item.strip() for item in (value or "").split(separator) if item.strip()]


def parse_args() -> argparse.Namespace:
    default_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "processed"
        / "chatbot"
        / "disease_knowledge.csv"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=default_path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.csv.is_file():
        raise FileNotFoundError(args.csv)

    with args.csv.open("r", encoding="utf-8-sig", newline="") as handle:
        records = list(csv.DictReader(handle))

    db = SessionLocal()
    try:
        for raw in records:
            item = (
                db.query(DiseaseKnowledge)
                .filter(DiseaseKnowledge.label == raw["label"])
                .first()
            )
            if not item:
                item = DiseaseKnowledge(label=raw["label"])
                db.add(item)

            item.label_id = int(raw["label_id"])
            item.name_vi = raw["name_vi"]
            item.name_en = raw["name_en"]
            item.icd10 = raw["icd10"] or None
            for field in LIST_FIELDS:
                setattr(item, field, split_list(raw.get(field)))
            item.contagious = raw["contagious"].casefold() == "true"
            item.summary = raw["summary"]
            item.when_to_see_doctor = raw["when_to_see_doctor"]
            item.urgency_level = raw["urgency_level"]
            item.sources = split_list(raw.get("sources"), "|")
            item.medical_review_date = date.fromisoformat(
                raw["medical_review_date"]
            )
        db.commit()
        print(f"Upserted {len(records)} disease knowledge records.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
