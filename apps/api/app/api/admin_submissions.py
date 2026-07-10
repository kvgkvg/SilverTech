from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import require_admin_token
from app.schemas.errors import friendly_error
from app.schemas.templates import SubmissionReview
from app.services.promotion_service import PromotionError
from app.services.review_service import AlreadyReviewedError, review_submission
from app.services.submission_service import get_submission, list_submissions

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_token)],
)


@router.post("/submissions/{submission_id}/review")
def review(submission_id: str, payload: SubmissionReview) -> dict:
    try:
        return review_submission(
            submission_id,
            payload.decision,
            payload.reviewer_note,
            payload.edited_template,
        )
    except KeyError as exc:
        raise friendly_error(404, "Khong tim thay mau gui len.", "try_again") from exc
    except AlreadyReviewedError as exc:
        raise friendly_error(409, "Mau gui len da duoc duyet roi.", "try_again") from exc
    except PromotionError as exc:
        raise friendly_error(400, "Nhan cua mau gui len chua dung.", "try_again") from exc
    except ValueError as exc:
        raise friendly_error(400, "Quyet dinh duyet khong hop le.", "try_again") from exc


@router.get("/submissions")
def list_pending(status: str | None = None) -> list[dict]:
    return list_submissions(status)


@router.get("/submissions/{submission_id}")
def read_submission(submission_id: str) -> dict:
    try:
        return get_submission(submission_id)
    except KeyError as exc:
        raise friendly_error(404, "Khong tim thay mau gui len.", "try_again") from exc
