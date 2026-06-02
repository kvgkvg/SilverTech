from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Template:
    id: str
    device_id: str
    template_code: str
    template_image_url: str
    logo_bbox: dict[str, Any] | None
    panel_bbox: dict[str, Any] | None
    feature_descriptor_path: str | None
    version: int
    status: str
    created_at: str
    updated_at: str
