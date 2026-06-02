from __future__ import annotations

from fastapi import APIRouter

from app.schemas.errors import friendly_error
from app.schemas.templates import SubmissionReview
from app.services.review_service import review_submission

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/submissions/{submission_id}/review")
def review(submission_id: str, payload: SubmissionReview) -> dict:
    try:
        return review_submission(submission_id, payload.decision, payload.reviewer_note)
    except KeyError as exc:
        raise friendly_error(404, "Khong tim thay mau gui len.", "try_again") from exc
    except ValueError as exc:
        raise friendly_error(400, "Quyet dinh duyet khong hop le.", "try_again") from exc
