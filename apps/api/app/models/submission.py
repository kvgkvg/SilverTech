from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Submission:
    id: str
    submitted_by: str | None
    brand: str
    appliance_type: str
    image_url: str
    proposed_labels_json: dict[str, Any]
    status: str
    reviewer_note: str | None
    created_at: str
