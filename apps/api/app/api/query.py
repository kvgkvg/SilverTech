from __future__ import annotations

from fastapi import APIRouter

from app.schemas.errors import ERRORS, friendly_error
from app.schemas.templates import GuidanceOutput, QueryRequest
from app.services.guidance_service import GuidanceError, create_guidance

router = APIRouter(prefix="/api", tags=["guidance"])


@router.post("/query", response_model=GuidanceOutput)
def query(payload: QueryRequest) -> dict:
    try:
        return create_guidance(payload.template_id, payload.user_query_text)
    except GuidanceError as exc:
        key = str(exc)
        message, action = ERRORS.get(key, ERRORS["invalid_button"])
        if key == "missing_template":
            status = 404
        elif key == "llm_failed":
            status = 502
        else:
            status = 409
        raise friendly_error(status, message, action) from exc
