from __future__ import annotations

from typing import Any

import numpy as np

from app.services.template_repository import get_template, list_candidates
from app.storage.database import ROOT

_FAILURE_RECOVERY = {
    "low_confidence": "rescan",
    "no_logo": "scan_wider",
    "glare": "reduce_glare",
    "partial_view": "move_closer",
}


def _decode_gray(image_bytes: bytes) -> "np.ndarray":
    import cv2

    buf = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("could not decode image bytes")
    return img


def _template_assets(template: dict[str, Any]):
    """Return (template_gray | None, keypoints | None, descriptors | None)."""
    import cv2

    from scripts.build_descriptors import load_descriptors

    descriptor_url = template.get("feature_descriptor_url")
    if descriptor_url:
        npz_path = ROOT / descriptor_url
        if npz_path.exists():
            try:
                kp, desc = load_descriptors(str(npz_path))
                return None, kp, desc
            except Exception:
                pass  # corrupt/invalid .npz -> fall back to template image
    image_url = template.get("template_image_url")
    if image_url:
        img_path = ROOT / image_url
        if img_path.exists() and img_path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            return cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE), None, None
    return None, None, None


def _buttons_map(template: dict[str, Any]) -> dict[str, dict[str, float]]:
    return {b["button_id"]: b["bbox_template_coordinates"] for b in template.get("buttons", [])}


def match_frame(
    image_bytes: bytes,
    *,
    brand: str | None = None,
    appliance_type: str | None = None,
) -> dict[str, Any]:
    from scripts.match_images import match_images

    frame = _decode_gray(image_bytes)
    candidates = list_candidates(brand, appliance_type) or list_candidates(None, None)

    best: dict[str, Any] | None = None
    best_template_id: str | None = None
    for summary in candidates:
        template = get_template(summary["id"])
        if template is None or not template.get("buttons"):
            continue
        tpl_gray, kp, desc = _template_assets(template)
        if tpl_gray is None and desc is None:
            continue  # placeholder template with no real image/descriptors
        result = match_images(
            tpl_gray,
            frame,
            _buttons_map(template),
            template_keypoints=kp,
            template_descriptors=desc,
        )
        if result.get("accepted"):
            if best is None or result["match_score"] > best["match_score"]:
                best = result
                best_template_id = template["id"]

    if best is None:
        return {
            "accepted": False,
            "failure_reason": "low_confidence",
            "recovery_action": "rescan",
            "projected_buttons": [],
        }

    polygons = [
        {"button_id": bid, "polygon": poly}
        for bid, poly in best["projected_buttons"].items()
    ]
    return {
        "accepted": True,
        "template_id": best_template_id,
        "match_score": best["match_score"],
        "inlier_count": best["inlier_count"],
        "inlier_ratio": best["inlier_ratio"],
        "reprojection_error": best["reprojection_error"],
        "projected_buttons": polygons,
    }
