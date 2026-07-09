from __future__ import annotations

import os
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
    started = time.perf_counter()
    template = get_template(template_id)
    if template is None:
        raise GuidanceError("missing_template")
    prompt_summary = build_prompt_summary(template, user_query)
    if os.getenv("SILVERTECH_LLM_PROVIDER", "mock").strip().lower() != "mock":
        time.sleep(1.2)
    try:
        raw = LLMService().generate(user_query, template)
    except LLMProviderError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        write_llm_log(
            template_id=template_id,
            user_query=user_query,
            stt_text=None,
            prompt_summary=prompt_summary,
            raw_response={"error": str(exc)},
            validated_steps=None,
            validation_status="rejected",
            latency_ms=latency_ms,
        )
        raise GuidanceError("llm_failed") from exc
    try:
        guidance = parse_guidance(raw)
        validate_guidance_buttons(template_id, guidance)
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        write_llm_log(
            template_id=template_id,
            user_query=user_query,
            stt_text=None,
            prompt_summary=prompt_summary,
            raw_response=raw,
            validated_steps=None,
            validation_status="rejected",
            latency_ms=latency_ms,
        )
        raise GuidanceError("invalid_button") from exc
    latency_ms = int((time.perf_counter() - started) * 1000)
    payload = guidance.model_dump()
    _humanize_instructions(payload, template)
    _attach_audio_urls(payload)
    write_llm_log(
        template_id=template_id,
        user_query=user_query,
        stt_text=None,
        prompt_summary=prompt_summary,
        raw_response=raw,
        validated_steps=payload,
        validation_status="accepted",
        latency_ms=latency_ms,
    )
    return payload


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
