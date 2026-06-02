from __future__ import annotations

import time
import uuid
from typing import Any

from app.models.common import encode_json
from app.storage.database import db_session


def write_llm_log(
    *,
    template_id: str,
    user_query: str,
    stt_text: str | None,
    prompt_summary: str,
    raw_response: Any,
    validated_steps: Any,
    validation_status: str,
    latency_ms: int,
) -> None:
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO llm_logs
            (id, template_id, user_query, stt_text, prompt_summary, raw_response,
             validated_steps_json, validation_status, latency_ms, created_at)
            VALUES (:id, :template_id, :user_query, :stt_text, :prompt_summary, :raw_response,
                    :validated_steps_json, :validation_status, :latency_ms, :created_at)
            """,
            {
                "id": str(uuid.uuid4()),
                "template_id": template_id,
                "user_query": user_query,
                "stt_text": stt_text,
                "prompt_summary": prompt_summary,
                "raw_response": encode_json(raw_response),
                "validated_steps_json": encode_json(validated_steps),
                "validation_status": validation_status,
                "latency_ms": latency_ms,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        )
