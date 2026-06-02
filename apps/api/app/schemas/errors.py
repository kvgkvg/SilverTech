from __future__ import annotations

from fastapi import HTTPException
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    message_vi: str
    recovery_action: str = Field(
        pattern="^(rescan|move_closer|reduce_glare|scan_wider|manual_select|type_query|try_again)$"
    )


def friendly_error(status_code: int, message_vi: str, recovery_action: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=ErrorResponse(message_vi=message_vi, recovery_action=recovery_action).model_dump(),
    )


ERRORS = {
    "missing_template": ("Khong tim thay mau thiet bi. Vui long chon lai thiet bi.", "manual_select"),
    "invalid_button": ("Huong dan chua chac chan. Vui long thu lai cau hoi.", "try_again"),
    "stt_failed": ("Khong nghe ro cau hoi. Vui long noi lai hoac nhap bang chu.", "type_query"),
    "low_confidence": ("Chua nhan dien chac chan. Vui long quet lai gan hon.", "rescan"),
}
