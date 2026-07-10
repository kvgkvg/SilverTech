from __future__ import annotations

from typing import Any

from app.models.common import decode_json
from app.services.promotion_service import PromotionError, promote_submission
from app.storage.database import db_session

_DECISIONS = {"accept", "edit", "reject"}


class AlreadyReviewedError(Exception):
    """The submission has already been accepted or rejected."""


def review_submission(
    submission_id: str,
    decision: str,
    reviewer_note: str | None,
    edited_template: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if decision not in _DECISIONS:
        raise ValueError("decision must be accept, edit, or reject")
    if decision == "edit" and not edited_template:
        raise PromotionError("edit requires edited_template")

    with db_session() as conn:
        row = conn.execute(
            "SELECT status, proposed_labels_json FROM submissions WHERE id = :id",
            {"id": submission_id},
        ).fetchone()
        if row is None:
            raise KeyError(submission_id)
        if row["status"] != "pending":
            raise AlreadyReviewedError(submission_id)

        template_id: str | None = None
        if decision == "reject":
            status = "rejected"
        else:
            status = "accepted"
            labels = (
                edited_template
                if decision == "edit"
                else decode_json(row["proposed_labels_json"], default={})
            )
            # Raises inside the session, so the UPDATE below never lands.
            template_id = promote_submission(conn, submission_id, labels)

        conn.execute(
            "UPDATE submissions SET status = :status, reviewer_note = :note WHERE id = :id",
            {"status": status, "note": reviewer_note, "id": submission_id},
        )
    return {"submission_id": submission_id, "status": status, "template_id": template_id}
