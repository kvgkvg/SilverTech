from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LLMLog:
    id: str
    template_id: str
    user_query: str
    stt_text: str | None
    prompt_summary: str
    raw_response: dict[str, Any] | str | None
    validated_steps_json: dict[str, Any] | None
    validation_status: str
    latency_ms: int
    created_at: str
