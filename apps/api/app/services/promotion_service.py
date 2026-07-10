from __future__ import annotations

import shutil
import sqlite3
import time
from typing import Any

from app.models.common import BUTTON_TYPES, encode_json
from app.services.vision_tools_path import ensure_vision_tools_on_path
from app.storage.database import ROOT
from app.storage.seed import is_labeled_button

ensure_vision_tools_on_path()

from scripts.logo_anchor import compute_button_offsets  # noqa: E402

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


def copy_submission_image(image_url: str, template_id: str) -> str:
    """Copy the submitted photo into data/templates/ and return its new url.

    data/submissions/ is a queue: deleting it must not kill a live template.
    The destination name is built from template_id, which the server minted.
    No part of the request reaches the filesystem path.
    """
    source = (ROOT / image_url).resolve()
    submissions_dir = SUBMISSIONS_DIR.resolve()
    if source.parent != submissions_dir:
        raise PromotionError("the submission image must live in data/submissions/")

    suffix = source.suffix.lower()
    if suffix not in _ALLOWED_IMAGE_SUFFIXES:
        raise PromotionError(f"unsupported image type: {suffix or '(none)'}")
    if not source.is_file():
        raise PromotionError(f"the submission image is missing: {image_url}")

    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    templates_dir = TEMPLATES_DIR.resolve()
    destination = (templates_dir / f"{template_id}{suffix}").resolve()
    if destination.parent != templates_dir:
        raise PromotionError(f"template_id must not contain a path separator: {template_id!r}")

    shutil.copyfile(source, destination)
    return f"data/templates/{destination.name}"


def _short_id(submission_id: str) -> str:
    """Eight hex characters of the submission uuid.

    Two submissions could share a prefix. They would collide on a primary key
    inside the caller's transaction, roll it back, and write nothing.
    """
    return submission_id.replace("-", "")[:8]


def promote_submission(
    conn: sqlite3.Connection,
    submission_id: str,
    labels: dict[str, Any],
) -> str:
    """Insert devices/templates/buttons/button_offsets from reviewed labels.

    Returns the new template_id. The caller owns the transaction: a failed copy
    or a bad bbox must not leave an orphan devices row behind.
    """
    validate_labels(labels)

    sid = _short_id(submission_id)
    device_id = f"device_{sid}"
    template_id = f"template_{sid}"
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    device = labels["device"]
    template = labels["template"]
    buttons = labels["buttons"]
    logo_bbox = template["logo_bbox"]

    image_url = copy_submission_image(template["template_image_url"], template_id)

    # Statuses are the server's to set. The wizard sends 'submitted' for the
    # device, which devices' CHECK (status IN ('active','archived')) forbids.
    conn.execute(
        """
        INSERT INTO devices
        (id, brand, appliance_type, model_name, display_name, status, created_at, updated_at)
        VALUES (:id, :brand, :appliance_type, :model_name, :display_name, 'active', :now, :now)
        """,
        {
            "id": device_id,
            "brand": device["brand"],
            "appliance_type": device["appliance_type"],
            "model_name": device.get("model_name"),
            "display_name": device["display_name"],
            "now": now,
        },
    )
    conn.execute(
        """
        INSERT INTO templates
        (id, device_id, template_code, template_image_url, logo_bbox, panel_bbox,
         feature_descriptor_path, version, status, created_at, updated_at)
        VALUES (:id, :device_id, :template_code, :template_image_url, :logo_bbox, :panel_bbox,
                NULL, 1, 'official', :now, :now)
        """,
        {
            "id": template_id,
            "device_id": device_id,
            "template_code": template["template_code"],
            "template_image_url": image_url,
            "logo_bbox": encode_json(logo_bbox),
            "panel_bbox": encode_json(template["panel_bbox"])
            if template.get("panel_bbox")
            else None,
            "now": now,
        },
    )
    for button in buttons:
        conn.execute(
            """
            INSERT INTO buttons
            (id, template_id, button_id, label, vietnamese_name, function_description,
             bbox_template_coordinates, polygon_template_coordinates, button_type,
             created_at, updated_at)
            VALUES (:id, :template_id, :button_id, :label, :vietnamese_name, :function_description,
                    :bbox, :polygon, :button_type, :now, :now)
            """,
            {
                "id": f"btn_{sid}_{button['button_id']}",
                "template_id": template_id,
                "button_id": button["button_id"],
                "label": button["label"],
                "vietnamese_name": button["vietnamese_name"],
                "function_description": button["function_description"],
                "bbox": encode_json(button["bbox_template_coordinates"]),
                "polygon": encode_json(button["polygon_template_coordinates"])
                if button.get("polygon_template_coordinates")
                else None,
                "button_type": button["button_type"],
                "now": now,
            },
        )

    # Without these rows run_logo_anchor raises 409 and the template is inert.
    offsets = compute_button_offsets(
        logo_bbox,
        {b["button_id"]: b["bbox_template_coordinates"] for b in buttons},
    )
    for button_id, offset in offsets.items():
        conn.execute(
            """
            INSERT INTO button_offsets (template_id, button_id, dx, dy, dw, dh, updated_at)
            VALUES (:template_id, :button_id, :dx, :dy, :dw, :dh, :now)
            """,
            {"template_id": template_id, "button_id": button_id, **offset, "now": now},
        )
    return template_id
