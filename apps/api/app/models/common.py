from __future__ import annotations

import json
from typing import Any


DEVICE_STATUSES = {"active", "archived"}
TEMPLATE_STATUSES = {"official", "submitted", "archived"}
SUBMISSION_STATUSES = {"pending", "accepted", "rejected"}
BUTTON_TYPES = {"physical", "touch", "dial", "display", "unknown"}
LLM_VALIDATION_STATUSES = {"accepted", "regenerated", "rejected", "error"}
VISION_FAILURE_REASONS = {
    "low_confidence",
    "no_logo",
    "glare",
    "partial_view",
    "unsupported",
    "wrong_brand",
    "blur",
}


def encode_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def decode_json(value: str | None, default: Any = None) -> Any:
    if value is None or value == "":
        return default
    return json.loads(value)


def require_enum(value: str, allowed: set[str], field: str) -> str:
    if value not in allowed:
        raise ValueError(f"{field} must be one of {sorted(allowed)}")
    return value
