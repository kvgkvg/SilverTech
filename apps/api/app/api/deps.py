from __future__ import annotations

import os
import secrets

from fastapi import Header

from app.schemas.errors import friendly_error


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    """Guard /api/admin, which writes the templates table the runtime serves from.

    Default closed: an unset SILVERTECH_ADMIN_TOKEN disables the router rather
    than disabling the check.
    """
    expected = os.getenv("SILVERTECH_ADMIN_TOKEN", "").strip()
    if not expected:
        raise friendly_error(503, "Chuc nang duyet chua duoc bat tren may chu.", "try_again")
    if not x_admin_token or not secrets.compare_digest(x_admin_token, expected):
        raise friendly_error(401, "Khong co quyen duyet.", "try_again")
