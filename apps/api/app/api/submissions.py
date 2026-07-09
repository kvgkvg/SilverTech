from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from app.schemas.errors import friendly_error
from app.schemas.templates import SubmissionCreate
from app.services.submission_service import create_submission
from app.storage.database import ROOT

router = APIRouter(prefix="/api", tags=["submissions"])

_ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@router.post("/submissions", status_code=201)
def submit_template(payload: SubmissionCreate) -> dict:
    try:
        submission_id = create_submission(payload.model_dump())
    except ValueError as exc:
        raise friendly_error(400, "Anh gui len chi duoc la bang dieu khien thiet bi.", "try_again") from exc
    return {"submission_id": submission_id, "status": "pending"}


@router.post("/submissions/image", status_code=201)
async def upload_submission_image(image: UploadFile = File(...)) -> dict:
    """Store a user-submitted panel photo and return its image_url for the
    follow-up POST /api/submissions call."""
    suffix = Path(image.filename or "").suffix.lower() or ".jpg"
    if suffix not in _ALLOWED_IMAGE_EXTENSIONS:
        raise friendly_error(400, "Anh phai la JPG, PNG hoac WEBP.", "try_again")
    data = await image.read()
    if not data:
        raise friendly_error(400, "Anh tai len bi rong.", "try_again")
    directory = ROOT / "data" / "submissions"
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{suffix}"
    (directory / filename).write_bytes(data)
    return {"image_url": f"data/submissions/{filename}"}
