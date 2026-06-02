from __future__ import annotations

from fastapi import APIRouter

from app.schemas.templates import VisionCandidateRequest, VisionCandidateResponse
from app.services.template_repository import list_candidates

router = APIRouter(prefix="/api/vision", tags=["vision"])


@router.post("/candidates", response_model=VisionCandidateResponse)
def get_candidates(payload: VisionCandidateRequest) -> dict:
    return {"candidates": list_candidates(payload.brand, payload.appliance_type)}
