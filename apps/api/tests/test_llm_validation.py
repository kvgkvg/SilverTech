from __future__ import annotations

import pytest

from app.schemas.templates import GuidanceOutput
from app.services.button_validator import validate_guidance_buttons


def test_valid_guidance_buttons_pass(client):
    guidance = GuidanceOutput(
        intent="quick_wash",
        steps=[
            {
                "step_number": 1,
                "instruction_vi": "Nhan nut Giat nhanh.",
                "button_id": "quick_wash",
                "expected_result": "Da chon giat nhanh.",
            }
        ],
    )
    validate_guidance_buttons("template_toshiba_washer_panel_v1", guidance)


def test_invalid_guidance_buttons_fail(client):
    guidance = GuidanceOutput(
        intent="unsafe",
        steps=[
            {
                "step_number": 1,
                "instruction_vi": "Nhan nut khong ton tai.",
                "button_id": "made_up_button",
                "expected_result": "Khong hop le.",
            }
        ],
    )
    with pytest.raises(ValueError):
        validate_guidance_buttons("template_toshiba_washer_panel_v1", guidance)
