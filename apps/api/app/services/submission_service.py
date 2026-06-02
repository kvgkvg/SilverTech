from __future__ import annotations

import time
import uuid

from app.models.common import encode_json
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
