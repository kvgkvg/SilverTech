from __future__ import annotations

from fastapi import APIRouter

from app.schemas.errors import friendly_error
from app.schemas.templates import SubmissionCreate
from app.services.submission_service import create_submission

router = APIRouter(prefix="/api", tags=["submissions"])


@router.post("/submissions", status_code=201)
def submit_template(payload: SubmissionCreate) -> dict:
    try:
        submission_id = create_submission(payload.model_dump())
    except ValueError as exc:
        raise friendly_error(400, "Anh gui len chi duoc la bang dieu khien thiet bi.", "try_again") from exc
    return {"submission_id": submission_id, "status": "pending"}
