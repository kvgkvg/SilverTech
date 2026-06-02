from __future__ import annotations

from app.storage.database import db_session


def review_submission(submission_id: str, decision: str, reviewer_note: str | None) -> dict:
    if decision not in {"accept", "edit", "reject"}:
        raise ValueError("decision must be accept, edit, or reject")
    status = "accepted" if decision in {"accept", "edit"} else "rejected"
    with db_session() as conn:
        found = conn.execute("SELECT id FROM submissions WHERE id = :id", {"id": submission_id}).fetchone()
        if found is None:
            raise KeyError(submission_id)
        conn.execute(
            "UPDATE submissions SET status = :status, reviewer_note = :note WHERE id = :id",
            {"status": status, "note": reviewer_note, "id": submission_id},
        )
    return {"submission_id": submission_id, "status": status, "template_id": None}
