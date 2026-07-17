from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

CHATBOT_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = CHATBOT_DIR / "prompts"
RULES_DIR = CHATBOT_DIR / "rules"

SYSTEM_PROMPT_FILE = PROMPTS_DIR / "medical_chat_system.md"
USER_TEMPLATE_NAME = "medical_chat_user_template.j2"
FALLBACK_RESPONSE_FILE = PROMPTS_DIR / "fallback_response_template.md"


@lru_cache(maxsize=16)
def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


@lru_cache(maxsize=8)
def load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a mapping: {path}")
    return data


@lru_cache(maxsize=1)
def get_template_env():
    from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

    return Environment(
        loader=FileSystemLoader(str(PROMPTS_DIR)),
        autoescape=select_autoescape(default=False),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )


def get_system_prompt() -> str:
    return load_text(SYSTEM_PROMPT_FILE)


def get_fallback_response_template() -> str:
    return load_text(FALLBACK_RESPONSE_FILE)


def render_user_prompt(payload: dict[str, Any]) -> str:
    template = get_template_env().get_template(USER_TEMPLATE_NAME)
    return template.render(**payload).strip()


def load_retrieval_rules() -> dict[str, Any]:
    return load_yaml(RULES_DIR / "retrieval_rules.yaml")


def load_medical_safety_rules() -> dict[str, Any]:
    return load_yaml(RULES_DIR / "medical_safety_rules.yaml")


def load_prompt_injection_rules() -> dict[str, Any]:
    return load_yaml(RULES_DIR / "prompt_injection_rules.yaml")
