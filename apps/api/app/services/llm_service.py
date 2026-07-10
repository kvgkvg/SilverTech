from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


class LLMProviderError(RuntimeError):
    pass


class LLMService:
    """
    Service adapter for generating step-by-step guidance via a language model or mock.
    """

    def generate(self, user_query: str, template: dict[str, Any]) -> dict[str, Any]:
        """
        Generate guidance steps for a given user query and template.

        Args:
            user_query (str): The Vietnamese voice transcription or text query.
            template (dict[str, Any]): The matched appliance template database record.

        Returns:
            dict[str, Any]: Parsed JSON dictionary containing steps and safety notes.
        """
        provider = os.getenv("SILVERTECH_LLM_PROVIDER", "mock").strip().lower()
        if provider == "mock":
            return _mock_guidance(user_query, template)
        if provider == "openrouter":
            return _generate_openrouter(user_query, template)
        raise LLMProviderError(f"Unsupported LLM provider: {provider}")


def _generate_openrouter(user_query: str, template: dict[str, Any]) -> dict[str, Any]:
    """
    Call the OpenRouter API to generate structured guidance using an LLM.

    Args:
        user_query (str): The user's query in Vietnamese.
        template (dict[str, Any]): The matched template database record.

    Raises:
        LLMProviderError: If credentials/options are missing or if the API call fails.

    Returns:
        dict[str, Any]: The parsed JSON response matching the guidance schema.
    """
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise LLMProviderError("OPENROUTER_API_KEY is not configured")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    model = os.getenv("OPENROUTER_MODEL", "").strip()
    if not model:
        raise LLMProviderError("OPENROUTER_MODEL is not configured")

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": _system_prompt(),
            },
            {
                "role": "user",
                "content": _user_prompt(user_query, template),
            },
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    referer = os.getenv("OPENROUTER_HTTP_REFERER", "").strip()
    app_title = os.getenv("OPENROUTER_APP_TITLE", "").strip()
    if referer:
        headers["HTTP-Referer"] = referer
    if app_title:
        headers["X-Title"] = app_title

    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise LLMProviderError(f"OpenRouter HTTP {exc.code}: {detail}") from exc
    except Exception as exc:
        raise LLMProviderError(f"OpenRouter request failed: {exc}") from exc

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMProviderError(f"OpenRouter response missing message content: {body}") from exc
    return _parse_json_content(content)


def _parse_json_content(content: Any) -> dict[str, Any]:
    """
    Sanitize and parse raw string content from LLM into a dictionary.

    Args:
        content (Any): The content returned by the LLM (string or dict).

    Raises:
        LLMProviderError: If the content is not valid JSON or not a dictionary.

    Returns:
        dict[str, Any]: Parsed JSON dictionary.
    """
    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        raise LLMProviderError("LLM returned non-JSON content")
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMProviderError(f"LLM returned invalid JSON: {text}") from exc
    if not isinstance(parsed, dict):
        raise LLMProviderError("LLM JSON root must be an object")
    return parsed


def _system_prompt() -> str:
    """
    Build the system instructions to enforce the JSON schema and correct button references.

    Returns:
        str: The system prompt string.
    """
    return (
        "You are SilverTech's appliance guidance engine for elderly Vietnamese users. "
        "Return JSON only. The JSON must match exactly this schema: "
        "{"
        '"intent": string, '
        '"steps": [{"step_number": integer starting at 1, '
        '"instruction_vi": Vietnamese instruction, '
        '"button_id": one valid button_id from the provided template only, '
        '"expected_result": Vietnamese expected result}], '
        '"safety_note": Vietnamese string or null'
        "}. "
        "Use only the provided template buttons and their descriptions. "
        "Do not invent button IDs. Keep each instruction short, direct, and safe. "
        "instruction_vi and expected_result are read aloud by a Vietnamese "
        "text-to-speech engine, so they must never contain a raw button_id such as "
        "'time_1_min'. Refer to a button by its vietnamese_name instead. "
        "If the question is NOT about operating this specific appliance (small talk, "
        "recipes, weather, other devices, anything unrelated), refuse: return "
        '{"intent": "out_of_scope", "steps": [], "safety_note": a short polite '
        "Vietnamese sentence explaining you can only help with this appliance}."
    )


def _user_prompt(user_query: str, template: dict[str, Any]) -> str:
    """
    Build the user prompt containing the question and database context of template buttons.

    Args:
        user_query (str): The Vietnamese voice transcription/query text.
        template (dict[str, Any]): Matched template database record.

    Returns:
        str: The user prompt string.
    """
    buttons = [
        {
            "button_id": button["button_id"],
            "label": button["label"],
            "vietnamese_name": button["vietnamese_name"],
            "function_description": _compact(button["function_description"], 900),
        }
        for button in template.get("buttons", [])
    ]
    template_context = {
        "template_id": template["id"],
        "brand": template["brand"],
        "appliance_type": template["appliance_type"],
        "template_code": template["template_code"],
        "buttons": buttons,
    }
    return (
        "User question in Vietnamese:\n"
        f"{user_query}\n\n"
        "Matched template and button database context:\n"
        f"{json.dumps(template_context, ensure_ascii=False)}\n\n"
        "Create step-by-step guidance using the minimum necessary steps."
    )


def _compact(text: str, limit: int) -> str:
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def _mock_guidance(user_query: str, template: dict[str, Any]) -> dict[str, Any]:
    query = user_query.lower()
    buttons = {b["button_id"]: b for b in template["buttons"]}
    if "nướng" in query or "nuong" in query:
        button_id = "grill" if "grill" in buttons else next(iter(buttons))
        intent = "grill"
        instruction = "Nhấn nút Nướng để chọn chế độ nướng."
    elif "giặt nhanh" in query or "giat nhanh" in query:
        button_id = "quick_wash" if "quick_wash" in buttons else next(iter(buttons))
        intent = "quick_wash"
        instruction = "Nhấn nút Giặt nhanh để chọn chương trình giặt nhanh."
    elif "rã đông" in query or "ra dong" in query:
        button_id = "turbo_defrost" if "turbo_defrost" in buttons else next(iter(buttons))
        intent = "defrost"
        instruction = "Nhấn nút Rã đông để chọn chế độ rã đông."
    elif "nhiệt độ" in query or "nhiet do" in query:
        button_id = "temp_up" if "temp_up" in buttons else next(iter(buttons))
        intent = "temperature"
        instruction = "Nhấn nút Tăng nhiệt độ để chỉnh nhiệt độ."
    elif "hẹn giờ" in query or "hen gio" in query:
        button_id = "time_clock" if "time_clock" in buttons else next(iter(buttons))
        intent = "timer"
        instruction = "Nhấn nút Hẹn giờ/Đồng hồ."
    else:
        # Unknown query: refuse instead of guessing a button. Telling an elderly
        # user to press an arbitrary button is worse than admitting no answer.
        return {
            "intent": "out_of_scope",
            "steps": [],
            "safety_note": (
                "Câu hỏi này không liên quan đến thiết bị. "
                "Bà/ông hãy hỏi về cách sử dụng các nút trên bảng điều khiển nhé."
            ),
        }
    return {
        "intent": intent,
        "steps": [
            {
                "step_number": 1,
                "instruction_vi": instruction,
                "button_id": button_id,
                "expected_result": "Lò chọn đúng chức năng trên bảng điều khiển.",
            }
        ],
        "safety_note": None,
    }
