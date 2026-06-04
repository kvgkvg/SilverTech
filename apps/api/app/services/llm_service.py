from __future__ import annotations

import json
import os
from typing import Any
from urllib.request import Request, urlopen


DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "qwen/qwen3.7-plus"


class LLMService:
    def generate(self, user_query: str, template: dict[str, Any]) -> dict[str, Any]:
        provider = os.getenv("SILVERTECH_LLM_PROVIDER", "mock").lower()
        if provider == "openrouter":
            return self._generate_openrouter(user_query, template)
        return self._generate_mock(user_query, template)

    def _generate_mock(self, user_query: str, template: dict[str, Any]) -> dict[str, Any]:
        query = user_query.lower()
        buttons = {b["button_id"]: b for b in template["buttons"]}
        if "nhiệt" in query or "nhiet" in query:
            button_id = "temp_up" if "temp_up" in buttons else next(iter(buttons))
            instruction = "Nhấn nút tăng nhiệt độ một lần."
            intent = "adjust_temperature"
        elif "sấy" in query or "say" in query:
            button_id = "dry_mode" if "dry_mode" in buttons else next(iter(buttons))
            instruction = "Nhấn nút Sấy để chọn chế độ sấy."
            intent = "dry_mode"
        elif "bắt đầu" in query or "bat dau" in query or "start" in query:
            button_id = "start_pause" if "start_pause" in buttons else next(iter(buttons))
            instruction = "Nhấn nút Bắt đầu để chạy chương trình."
            intent = "find_start"
        else:
            button_id = "quick_wash" if "quick_wash" in buttons else next(iter(buttons))
            instruction = "Nhấn nút Giặt nhanh để chọn chương trình giặt nhanh."
            intent = "quick_wash"
        return {
            "intent": intent,
            "steps": [
                {
                    "step_number": 1,
                    "instruction_vi": instruction,
                    "button_id": button_id,
                    "expected_result": "Máy chọn đúng chức năng trên bảng điều khiển.",
                }
            ],
            "safety_note": None,
        }

    def _generate_openrouter(self, user_query: str, template: dict[str, Any]) -> dict[str, Any]:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is required when SILVERTECH_LLM_PROVIDER=openrouter"
            )

        base_url = os.getenv("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL).rstrip("/")
        model = os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
        body = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": _openrouter_system_prompt(),
                },
                {
                    "role": "user",
                    "content": _openrouter_user_prompt(user_query, template),
                },
            ],
            "temperature": 0.2,
            "max_tokens": 800,
            "response_format": {"type": "json_object"},
        }
        request = Request(
            f"{base_url}/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers=_openrouter_headers(api_key),
            method="POST",
        )
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return _parse_openrouter_guidance(payload)


def _openrouter_headers(api_key: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    referer = os.getenv("OPENROUTER_HTTP_REFERER")
    title = os.getenv("OPENROUTER_APP_TITLE")
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-OpenRouter-Title"] = title
    return headers


def _openrouter_system_prompt() -> str:
    return (
        "You are SilverTech, an elderly-first Vietnamese appliance guidance assistant. "
        "Process the user's Vietnamese query together with the provided template database. "
        "Return JSON only for client-side processing, with no Markdown, prose, or code fences. "
        "The JSON schema is "
        '{"intent":"string","steps":[{"step_number":1,"instruction_vi":"string",'
        '"button_id":"string","expected_result":"string"}],"safety_note":null}. '
        "The steps array must show what the user needs to do step by step. "
        "Each step must contain one clear user action, use sequential step_number values, "
        "and reference exactly one valid button_id from the template database. "
        "Write instruction_vi and expected_result in simple Vietnamese for elderly users. "
        "Do not invent buttons, brands, modes, sensors, or appliance features that are not in "
        "the template database. If the user's request cannot be handled with the valid buttons, "
        "return one safe step using the closest valid button only when it is clearly appropriate; "
        "otherwise return a brief Vietnamese safety_note asking the user to try a different query."
    )


def _openrouter_user_prompt(user_query: str, template: dict[str, Any]) -> str:
    valid_buttons = [
        {
            "button_id": button["button_id"],
            "vietnamese_name": button.get("vietnamese_name"),
            "function_description": button.get("function_description"),
        }
        for button in template.get("buttons", [])
    ]
    return json.dumps(
        {
            "task": "process_user_query_against_template_database",
            "user_query_text": user_query,
            "template_database": {
                "template_id": template.get("id"),
                "template_code": template.get("template_code"),
                "brand": template.get("brand"),
                "appliance_type": template.get("appliance_type"),
                "valid_buttons": valid_buttons,
            },
        },
        ensure_ascii=False,
    )


def _parse_openrouter_guidance(payload: dict[str, Any]) -> dict[str, Any]:
    content = payload["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    if not isinstance(content, str):
        raise ValueError("OpenRouter response content must be a JSON string")
    return json.loads(_strip_json_fences(content))


def _strip_json_fences(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped
