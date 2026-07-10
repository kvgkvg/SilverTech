from __future__ import annotations

import time

from app.services.button_validator import validate_guidance_buttons
from app.services.instruction_sanitizer import humanize_button_ids
from app.services.llm_log_service import write_llm_log
from app.services.llm_prompt_builder import build_prompt_summary
from app.services.llm_response_parser import parse_guidance
from app.services.llm_service import LLMProviderError, LLMService
from app.services.template_repository import get_template
from app.services.tts_service import TTSService, TTSServiceError


class GuidanceError(Exception):
    pass


def create_guidance(template_id: str, user_query: str) -> dict:
    """
    Generate, validate, and log step-by-step guidance for a template and query.

    Retrieves the template, builds the context prompt, invokes the LLM Service,
    enforces validation checks (ensuring all step buttons exist on the template),
    and records full latency and log telemetry to the database.

    Args:
        template_id (str): The ID of the appliance template.
        user_query (str): The user's query text or transcription.

    Raises:
        GuidanceError: "missing_template" if template is not found in database,
            "llm_failed" if API call fails, or "invalid_button" if validation fails.

    Returns:
        dict: The serialized dictionary of the validated GuidanceOutput.
    """
    started = time.perf_counter()
    template = get_template(template_id)
    if template is None:
        raise GuidanceError("missing_template")
    prompt_summary = build_prompt_summary(template, user_query)
    try:
        raw = LLMService().generate(user_query, template)
    except LLMProviderError as exc:
        _log_rejected_attempt(
            template_id=template_id,
            user_query=user_query,
            prompt_summary=prompt_summary,
            raw_response={"error": str(exc)},
            started=started,
        )
        raise GuidanceError("llm_failed") from exc
    try:
        guidance = parse_guidance(raw)
        validate_guidance_buttons(template_id, guidance)
    except Exception as exc:
        _log_rejected_attempt(
            template_id=template_id,
            user_query=user_query,
            prompt_summary=prompt_summary,
            raw_response=raw,
            started=started,
        )
        raise GuidanceError("invalid_button") from exc
    payload = guidance.model_dump()
    _humanize_instructions(payload, template)
    _attach_audio_urls(payload)
    _log_accepted_attempt(
        template_id=template_id,
        user_query=user_query,
        prompt_summary=prompt_summary,
        raw_response=raw,
        validated_steps=payload,
        started=started,
    )
    return payload


def _latency_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _log_rejected_attempt(
    *,
    template_id: str,
    user_query: str,
    prompt_summary: str,
    raw_response: dict,
    started: float,
) -> None:
    write_llm_log(
        template_id=template_id,
        user_query=user_query,
        stt_text=None,
        prompt_summary=prompt_summary,
        raw_response=raw_response,
        validated_steps=None,
        validation_status="rejected",
        latency_ms=_latency_ms(started),
    )


def _log_accepted_attempt(
    *,
    template_id: str,
    user_query: str,
    prompt_summary: str,
    raw_response: dict,
    validated_steps: dict,
    started: float,
) -> None:
    write_llm_log(
        template_id=template_id,
        user_query=user_query,
        stt_text=None,
        prompt_summary=prompt_summary,
        raw_response=raw_response,
        validated_steps=validated_steps,
        validation_status="accepted",
        latency_ms=_latency_ms(started),
    )


def _humanize_instructions(payload: dict, template: dict) -> None:
    buttons = template.get("buttons", [])
    for step in payload.get("steps", []):
        step["instruction_vi"] = humanize_button_ids(step["instruction_vi"], buttons)
        step["expected_result"] = humanize_button_ids(step["expected_result"], buttons)


def _attach_audio_urls(payload: dict) -> None:
    tts = TTSService()
    for step in payload.get("steps", []):
        try:
            step["audio_url"] = tts.synthesize(step["instruction_vi"])
        except TTSServiceError:
            step["audio_url"] = None
