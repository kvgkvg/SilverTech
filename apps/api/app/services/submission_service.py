from __future__ import annotations

import time
import uuid
from typing import Any

from app.models.common import decode_json, encode_json
from app.services.submission_validation_service import validate_panel_submission
from app.storage.database import db_session


def create_submission(payload: dict) -> str:
    validate_panel_submission(payload["image_url"], payload["proposed_labels_json"])
    submission_id = str(uuid.uuid4())
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO submissions
            (id, submitted_by, brand, appliance_type, image_url, proposed_labels_json,
             status, reviewer_note, created_at)
            VALUES (:id, :submitted_by, :brand, :appliance_type, :image_url, :proposed_labels_json,
                    'pending', NULL, :created_at)
            """,
            {
                **payload,
                "id": submission_id,
                "proposed_labels_json": encode_json(payload["proposed_labels_json"]),
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        )
    return submission_id


_SUBMISSION_COLUMNS = (
    "id, submitted_by, brand, appliance_type, image_url, status, reviewer_note, created_at"
)


def list_submissions(status: str | None = None) -> list[dict[str, Any]]:
    query = f"SELECT {_SUBMISSION_COLUMNS} FROM submissions"
    params: dict[str, Any] = {}
    if status:
        query += " WHERE status = :status"
        params["status"] = status
    query += " ORDER BY created_at DESC"
    with db_session() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def get_submission(submission_id: str) -> dict[str, Any]:
    with db_session() as conn:
        row = conn.execute(
            f"SELECT {_SUBMISSION_COLUMNS}, proposed_labels_json FROM submissions WHERE id = :id",
            {"id": submission_id},
        ).fetchone()
    if row is None:
        raise KeyError(submission_id)
    submission = dict(row)
    submission["proposed_labels_json"] = decode_json(submission["proposed_labels_json"], default={})
    return submission
