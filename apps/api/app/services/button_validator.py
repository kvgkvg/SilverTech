from __future__ import annotations

from app.schemas.templates import GuidanceOutput
from app.services.template_repository import valid_button_ids


def validate_guidance_buttons(template_id: str, guidance: GuidanceOutput) -> None:
    valid = valid_button_ids(template_id)
    invalid = [step.button_id for step in guidance.steps if step.button_id not in valid]
    if invalid:
        raise ValueError(f"Invalid button_id values for template {template_id}: {invalid}")
