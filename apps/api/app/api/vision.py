from __future__ import annotations

import time

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
    """
    Save a frame that failed logo detection to a local debug directory.

    This utility helps collect edge-case or low-quality photos from real-device
    runs so that detection thresholds can be tuned offline.

    Args:
        frame_bytes (bytes): Raw binary bytes of the failed camera frame.

    Returns:
        str: Absolute path to the saved debug image file.
    """
    DEBUG_FRAME_DIR.mkdir(parents=True, exist_ok=True)
    path = DEBUG_FRAME_DIR / f"fail_{time.strftime('%Y%m%d_%H%M%S')}.png"
    path.write_bytes(frame_bytes)
    return str(path)


@router.post("/candidates", response_model=VisionCandidateResponse)
def get_candidates(payload: VisionCandidateRequest) -> dict:
    """
    Retrieve candidate appliance templates filtered by brand and/or appliance type.

    Supports a fallback mode where the top candidate is returned if no specific
    filters are specified in the request.

    Args:
        payload (VisionCandidateRequest): Request schema with optional brand,
            appliance_type, and brand_confidence scores.

    Returns:
        dict: A dictionary containing the list of matching template summaries
            under the 'candidates' key.
    """
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
    """
    Perform logo-anchored template matching and project button coordinates.

    Matches the uploaded frame against known appliance templates (either auto-detected
    by logo or specified via template_id), estimates the homography transformation,
    and returns the coordinates of all interactive buttons projected onto the frame.

    Args:
        template_id (str | None, optional): Explicit template ID to match.
            If None, the backend automatically detects the brand logo in the frame.
        frame (UploadFile): The raw image file (JPEG/PNG) captured by the mobile camera.

    Raises:
        HTTPException: 404 if no matching template logo is found in the frame.
        HTTPException: 409 if the template lacks required bounding box metadata.
        HTTPException: 400 if the uploaded image cannot be decoded.

    Returns:
        dict: The matching result containing the matched template ID, confidence tier
            (HOMOGRAPHY_REFINED / LOGO_SIMILARITY), logo pose, and projected button quads.
    """
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
