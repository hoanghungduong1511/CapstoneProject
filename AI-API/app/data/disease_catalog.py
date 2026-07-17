from __future__ import annotations

import csv
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import settings


LIST_FIELDS = {
    "aliases",
    "common_signs",
    "common_symptoms",
    "risk_factors",
    "self_care",
    "avoid",
    "red_flags",
    "red_flag_questions",
    "differential_diagnosis",
    "ask_user_questions",
}


def _split(value: str | None, separator: str = ";") -> list[str]:
    return [item.strip() for item in (value or "").split(separator) if item.strip()]


@lru_cache(maxsize=1)
def load_disease_catalog() -> dict[str, dict[str, Any]]:
    path = Path(settings.DISEASE_KNOWLEDGE_PATH)
    if not path.is_file():
        raise FileNotFoundError(f"Disease knowledge file not found: {path}")

    catalog: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle):
            item: dict[str, Any] = dict(raw)
            for field in LIST_FIELDS:
                item[field] = _split(raw.get(field))
            item["sources"] = _split(raw.get("sources"), "|")
            item["label_id"] = int(raw["label_id"])
            item["contagious"] = str(raw.get("contagious", "")).casefold() == "true"
            catalog[raw["label"].upper()] = item
    return catalog


def normalize_disease_label(label: str | None) -> str | None:
    if not label:
        return None
    normalized = label.strip().upper()
    catalog = load_disease_catalog()
    if normalized in catalog:
        return normalized
    for key, item in catalog.items():
        aliases = {
            alias.casefold()
            for alias in [
                item["name_vi"],
                item["name_en"],
                *item["aliases"],
            ]
        }
        if label.strip().casefold() in aliases:
            return key
    return None


def _normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    without_accents = "".join(
        char for char in decomposed
        if unicodedata.category(char) != "Mn"
    )
    without_accents = without_accents.replace("đ", "d").replace("Đ", "d")
    return re.sub(r"\s+", " ", without_accents).strip()


def extract_disease_labels_from_text(text: str | None) -> list[str]:
    """Find disease labels explicitly mentioned by the user."""
    if not text:
        return []

    normalized_text = _normalize_text(text)
    matches: list[tuple[int, str]] = []
    for label, item in load_disease_catalog().items():
        aliases = {
            label,
            item["name_vi"],
            item["name_en"],
            *item["aliases"],
        }
        for alias in aliases:
            normalized_alias = _normalize_text(str(alias))
            if not normalized_alias:
                continue
            pattern = rf"(?<![a-z0-9]){re.escape(normalized_alias)}(?![a-z0-9])"
            if re.search(pattern, normalized_text):
                matches.append((len(normalized_alias), label))
                break

    labels: list[str] = []
    for _, label in sorted(matches, key=lambda item: item[0], reverse=True):
        if label not in labels:
            labels.append(label)
    return labels


def get_disease_metadata(label: str | None) -> dict[str, Any] | None:
    normalized = normalize_disease_label(label)
    return load_disease_catalog().get(normalized) if normalized else None


def list_disease_catalog() -> list[dict[str, Any]]:
    return [
        {
            "label_id": item["label_id"],
            "label": item["label"],
            "name_vi": item["name_vi"],
            "name_en": item["name_en"],
            "icd10": item["icd10"],
            "urgency_level": item["urgency_level"],
        }
        for item in sorted(
            load_disease_catalog().values(), key=lambda value: value["label_id"]
        )
    ]
