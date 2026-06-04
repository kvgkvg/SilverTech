from __future__ import annotations

import json
from typing import Any

from app.services.llm_service import LLMService


def _template() -> dict[str, Any]:
    return {
        "id": "template_daikin_ac_remote_v1",
        "brand": "Daikin",
        "appliance_type": "air_conditioner",
        "template_code": "daikin_ac_remote_v1",
        "buttons": [
            {
                "button_id": "temp_up",
                "vietnamese_name": "Tăng nhiệt độ",
                "function_description": "Tăng nhiệt độ điều hòa",
            }
        ],
    }


def test_openrouter_uses_qwen_model_and_parses_chat_completion(monkeypatch):
    captured: dict[str, Any] = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "intent": "adjust_temperature",
                                        "steps": [
                                            {
                                                "step_number": 1,
                                                "instruction_vi": "Nhấn nút Tăng nhiệt độ.",
                                                "button_id": "temp_up",
                                                "expected_result": "Nhiệt độ tăng lên.",
                                            }
                                        ],
                                        "safety_note": None,
                                    }
                                )
                            }
                        }
                    ]
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("SILVERTECH_LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    monkeypatch.setattr("app.services.llm_service.urlopen", fake_urlopen)

    guidance = LLMService().generate("Tôi muốn chỉnh nhiệt độ", _template())

    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["headers"]["Content-type"] == "application/json"
    assert captured["body"]["model"] == "qwen/qwen3.7-plus"
    assert captured["body"]["response_format"] == {"type": "json_object"}
    assert captured["body"]["messages"][0]["role"] == "system"
    system_prompt = captured["body"]["messages"][0]["content"]
    assert "JSON only" in system_prompt
    assert "client-side processing" in system_prompt
    assert "step_number" in system_prompt
    assert "instruction_vi" in system_prompt
    assert "button_id" in system_prompt
    assert "expected_result" in system_prompt
    assert "template database" in system_prompt
    assert "one clear user action" in system_prompt
    user_prompt = json.loads(captured["body"]["messages"][1]["content"])
    assert user_prompt["task"] == "process_user_query_against_template_database"
    assert user_prompt["user_query_text"] == "Tôi muốn chỉnh nhiệt độ"
    assert user_prompt["template_database"]["template_id"] == "template_daikin_ac_remote_v1"
    assert user_prompt["template_database"]["valid_buttons"][0]["button_id"] == "temp_up"
    assert captured["timeout"] == 30
    assert guidance["steps"][0]["button_id"] == "temp_up"


def test_openrouter_requires_api_key(monkeypatch):
    monkeypatch.setenv("SILVERTECH_LLM_PROVIDER", "openrouter")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    try:
        LLMService().generate("Tôi muốn chỉnh nhiệt độ", _template())
    except RuntimeError as exc:
        assert "OPENROUTER_API_KEY" in str(exc)
    else:
        raise AssertionError("OpenRouter provider should require OPENROUTER_API_KEY")
