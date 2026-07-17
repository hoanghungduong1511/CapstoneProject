"""Backward-compatible prompt builder import.

The chatbot prompt implementation lives in app.services.chatbot so long prompts
and rules can stay in .md/.j2/.yaml files instead of being hard-coded here.
"""

from app.services.chatbot.prompt_builder import (  # noqa: F401
    build_chat_prompt,
    build_debug_prompt_payload,
    sanitize_user_question,
)

