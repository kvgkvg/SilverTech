from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas.templates import VisionCandidateRequest, VisionCandidateResponse
from app.services.logo_anchor_service import LogoAnchorError, run_logo_anchor
from app.services.template_repository import list_candidates
from app.storage.database import ROOT

router = APIRouter(prefix="/api/vision", tags=["vision"])

# Frames that failed logo detection are dumped here so detection thresholds
# can be tuned against real photos instead of guesses (dev tool; safe to rm).
DEBUG_FRAME_DIR = ROOT / "data" / "debug_frames"


def _dump_failed_frame(frame_bytes: bytes) -> str:
    DEBUG_FRAME_DIR.mkdir(parents=True, exist_ok=True)
    path = DEBUG_FRAME_DIR / f"fail_{time.strftime('%Y%m%d_%H%M%S')}.png"
    path.write_bytes(frame_bytes)
    return str(path)


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


@router.post("/logo-anchor")
async def logo_anchor(
    template_id: str | None = Form(None),
    frame: UploadFile = File(...),
) -> dict:
    frame_bytes = await frame.read()
    try:
        result = run_logo_anchor(template_id, frame_bytes)
    except LogoAnchorError as exc:
        detail = exc.detail
        if exc.status_code == 404:
            dumped = _dump_failed_frame(frame_bytes)
            print(f"[VISION] logo-anchor FAILED, frame saved: {dumped}", flush=True)
            detail = f"{detail} [frame saved: {dumped}]"
        raise HTTPException(status_code=exc.status_code, detail=detail) from exc
    print(
        "[VISION] logo-anchor "
        f"requested={template_id or 'auto'} matched={result['template_id']} "
        f"tier={result['tier']} logo_pose={result['logo_pose']}",
        flush=True,
    )
    return result
