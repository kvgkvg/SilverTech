from __future__ import annotations

from typing import Any

from app.schemas.templates import GuidanceOutput


def parse_guidance(raw: dict[str, Any]) -> GuidanceOutput:
    return GuidanceOutput.model_validate(raw)
