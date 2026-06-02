from __future__ import annotations

import time
import uuid

from app.storage.database import db_session


def write_vision_log(payload: dict) -> str:
    if payload.get("accepted") and not payload.get("template_id"):
        raise ValueError("accepted vision logs require template_id")
    if not payload.get("accepted") and not payload.get("failure_reason"):
        raise ValueError("rejected vision logs require failure_reason")
    log_id = str(uuid.uuid4())
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO vision_logs
            (id, template_id, brand_candidate, match_score, inlier_count, inlier_ratio,
             reprojection_error, accepted, failure_reason, created_at)
            VALUES (:id, :template_id, :brand_candidate, :match_score, :inlier_count, :inlier_ratio,
                    :reprojection_error, :accepted, :failure_reason, :created_at)
            """,
            {
                **payload,
                "id": log_id,
                "accepted": 1 if payload.get("accepted") else 0,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        )
    return log_id
