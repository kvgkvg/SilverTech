from __future__ import annotations

import os
import time

from app.services.button_validator import validate_guidance_buttons
from app.services.llm_log_service import write_llm_log
from app.services.llm_prompt_builder import build_prompt_summary
from app.services.llm_response_parser import parse_guidance
from app.services.llm_service import LLMProviderError, LLMService
from app.services.template_repository import get_template


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
