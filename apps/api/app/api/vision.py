from __future__ import annotations

from fastapi import APIRouter

from app.schemas.templates import VisionCandidateRequest, VisionCandidateResponse
from app.services.template_repository import list_candidates

router = APIRouter(prefix="/api/vision", tags=["vision"])


@router.post("/candidates", response_model=VisionCandidateResponse)
def get_candidates(payload: VisionCandidateRequest) -> dict:
    top_one_fallback = (
        payload.brand_confidence == 0
        and payload.brand is None
        and payload.appliance_type is None
    )
    candidates = list_candidates(
        payload.brand,
        payload.appliance_type,
        limit=1 if top_one_fallback else None,
    )
    print(
        "[VISION] candidates "
        f"brand={payload.brand} appliance_type={payload.appliance_type} "
        f"brand_confidence={payload.brand_confidence} "
        f"top_one_fallback={top_one_fallback} count={len(candidates)}",
        flush=True,
    )
    return {"candidates": candidates}
