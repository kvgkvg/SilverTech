from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Button:
    id: str
    template_id: str
    button_id: str
    label: str
    vietnamese_name: str
    function_description: str
    bbox_template_coordinates: dict[str, Any]
    polygon_template_coordinates: list[dict[str, float]] | None
    button_type: str
    created_at: str
    updated_at: str
