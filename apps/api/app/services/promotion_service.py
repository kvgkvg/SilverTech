from __future__ import annotations

from typing import Any

from app.models.common import BUTTON_TYPES
from app.storage.database import ROOT
from app.storage.seed import is_labeled_button

SUBMISSIONS_DIR = ROOT / "data" / "submissions"
TEMPLATES_DIR = ROOT / "data" / "templates"

# Mirrors submissions.py:15. The suffix of the file already on disk decides the
# copy's extension; nothing from the request names a path.
_ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


class PromotionError(ValueError):
    """Reviewed labels cannot become a template."""


def _positive_box(bbox: Any) -> bool:
    if not isinstance(bbox, dict):
        return False
    return float(bbox.get("width", 0)) > 0 and float(bbox.get("height", 0)) > 0


def validate_labels(labels: dict[str, Any]) -> None:
    """Refuse anything that would break detection later. Never repair."""
    template = labels.get("template") or {}
    buttons = labels.get("buttons") or []

    if not _positive_box(template.get("logo_bbox")):
        raise PromotionError("logo_bbox is missing or has no positive size")
    if not buttons:
        raise PromotionError("the submission has no buttons")

    seen: set[str] = set()
    for button in buttons:
        if not is_labeled_button(button):
            raise PromotionError(f"button {button.get('button_id')!r} has no name")
        button_id = button["button_id"]
        if button_id in seen:
            raise PromotionError(f"duplicate button_id: {button_id}")
        seen.add(button_id)
        if not _positive_box(button.get("bbox_template_coordinates")):
            raise PromotionError(f"button {button_id} has a degenerate bbox")
        if button.get("button_type") not in BUTTON_TYPES:
            raise PromotionError(f"button {button_id} has an unknown button_type")
