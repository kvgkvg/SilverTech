from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile

from app.schemas.templates import VisionMatchResponse
from app.services.match_service import match_frame
from app.services.vision_log_service import write_vision_log

router = APIRouter(prefix="/api/vision", tags=["vision"])


@router.post("/match", response_model=VisionMatchResponse)
async def match(
    file: UploadFile = File(...),
    brand: str | None = Form(default=None),
    appliance_type: str | None = Form(default=None),
) -> dict:
    image_bytes = await file.read()
    result = match_frame(image_bytes, brand=brand, appliance_type=appliance_type)
    try:
        write_vision_log(
            {
                "template_id": result.get("template_id"),
                "brand_candidate": brand,
                "match_score": result.get("match_score"),
                "inlier_count": result.get("inlier_count"),
                "inlier_ratio": result.get("inlier_ratio"),
                "reprojection_error": result.get("reprojection_error"),
                "accepted": result["accepted"],
                "failure_reason": result.get("failure_reason"),
            }
        )
    except Exception:
        pass  # telemetry must not break detection
    return result
