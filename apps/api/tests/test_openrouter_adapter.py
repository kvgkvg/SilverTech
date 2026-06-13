from __future__ import annotations

import pytest

from app.services.llm_service import _parse_json_content, _user_prompt

TEMPLATE = {
    "id": "t1",
    "brand": "Toshiba",
    "appliance_type": "washing_machine",
    "template_code": "toshiba_v1",
    "buttons": [
        {
            "button_id": "quick_wash",
            "label": "Quick",
            "vietnamese_name": "Giat nhanh",
            "function_description": "Chon che do giat nhanh",
        }
    ],
}


def test_user_prompt_lists_valid_button_ids():
    prompt = _user_prompt("Giat nhanh the nao?", TEMPLATE)
    assert "quick_wash" in prompt
    assert "Giat nhanh the nao?" in prompt


def test_parse_json_content_strips_code_fence():
    fenced = '```json\n{"intent": "x", "steps": []}\n```'
    assert _parse_json_content(fenced) == {"intent": "x", "steps": []}


def test_parse_json_content_rejects_non_object():
    with pytest.raises(Exception):
        _parse_json_content("[1, 2, 3]")
