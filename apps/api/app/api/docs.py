from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/api", tags=["docs"])


@router.get("/openapi-contract", response_class=PlainTextResponse)
def openapi_contract() -> str:
    return Path("apps/api/openapi.yaml").read_text(encoding="utf-8")
