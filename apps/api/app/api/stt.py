from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.templates import STTResponse
from app.services.stt_service import STTService

router = APIRouter(prefix="/api", tags=["stt"])


@router.post("/stt", response_model=STTResponse)
async def stt(request: Request) -> dict:
    data = await request.body()
    text, confidence = STTService().transcribe(data or None, locale="vi-VN")
    return {"text": text, "confidence": confidence}
