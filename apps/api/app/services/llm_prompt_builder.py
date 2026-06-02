from __future__ import annotations

from typing import Any


def build_prompt_summary(template: dict[str, Any], user_query: str) -> str:
    buttons = ", ".join(
        f"{b['button_id']}:{b['vietnamese_name']}" for b in template.get("buttons", [])
    )
    return f"Query='{user_query}'. Valid buttons: {buttons}"
