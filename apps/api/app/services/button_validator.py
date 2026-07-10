from __future__ import annotations

from app.schemas.templates import GuidanceOutput
from app.services.template_repository import valid_button_ids


def validate_guidance_buttons(template_id: str, guidance: GuidanceOutput) -> None:
    """
    Validate that all button IDs referenced in the LLM guidance steps exist on the template.

    This acts as a hard security boundary to prevent hallucinated button IDs from
    being shown to the user.

    Args:
        template_id (str): The ID of the matched appliance template.
        guidance (GuidanceOutput): The generated guidance object.

    Raises:
        ValueError: If any step references a button_id not registered on the template.
    """
    valid = valid_button_ids(template_id)
    invalid = [step.button_id for step in guidance.steps if step.button_id not in valid]
    if invalid:
        raise ValueError(f"Invalid button_id values for template {template_id}: {invalid}")
