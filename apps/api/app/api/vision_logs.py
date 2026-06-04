from __future__ import annotations

from fastapi import APIRouter

from app.schemas.errors import friendly_error
from app.schemas.templates import VisionLogRequest
from app.services.vision_log_service import write_vision_log

router = APIRouter(prefix="/api", tags=["vision-logs"])


@router.post("/vision/logs")
def ingest_vision_log(payload: VisionLogRequest) -> dict:
    try:
        log_id = write_vision_log(payload.model_dump())
    except ValueError as exc:
        raise friendly_error(400, "Thong tin nhan dien chua hop le.", "try_again") from exc
    print(
        "[VISION] log "
        f"id={log_id} accepted={payload.accepted} template_id={payload.template_id} "
        f"brand={payload.brand_candidate} match_score={payload.match_score} "
        f"inliers={payload.inlier_count} ratio={payload.inlier_ratio} "
        f"failure={payload.failure_reason}",
        flush=True,
    )
    return {"id": log_id}
