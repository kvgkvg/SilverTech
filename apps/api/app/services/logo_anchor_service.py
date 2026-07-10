from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover - environment dependent
    cv2 = None

from app.services.template_repository import get_template, list_candidates
from app.services.vision_tools_path import ensure_vision_tools_on_path
from app.storage.database import ROOT

ensure_vision_tools_on_path()

from scripts.brand_gallery import BrandLogo, detect_brand, load_gallery  # noqa: E402
from scripts.logo_anchor import LogoPose  # noqa: E402
from scripts.logo_anchor_match import (  # noqa: E402
    LOGO_SIFT_MIN_MATCHES,
    LOGO_SIFT_SOFT_MATCHES,
    LOGO_SOFT_MIN_REFINED,
    detect_logo,
    match_with_logo_anchor,
)

BRANDS_DIR = ROOT / "data" / "brands"
_brand_gallery_cache: list[BrandLogo] | None = None


def _brand_gallery() -> list[BrandLogo]:
    global _brand_gallery_cache
    if _brand_gallery_cache is None:
        _brand_gallery_cache = load_gallery(BRANDS_DIR) if BRANDS_DIR.is_dir() else []
    return _brand_gallery_cache


class LogoAnchorError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _template_image_path(image_url: str) -> Path:
    path = Path(image_url)
    return path if path.is_absolute() else ROOT / path


def _load_template_assets(template: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    """Return (template_img, logo_crop) or raise LogoAnchorError."""
    logo_bbox = template["logo_bbox"]
    image_path = _template_image_path(template["template_image_url"])
    template_img = cv2.imread(str(image_path))
    if template_img is None:
        raise LogoAnchorError(500, f"cannot read template image: {image_path}")
    x, y = int(logo_bbox["x"]), int(logo_bbox["y"])
    w, h = int(logo_bbox["width"]), int(logo_bbox["height"])
    return template_img, template_img[y : y + h, x : x + w]


def _detect_best_template(frame: np.ndarray) -> tuple[dict[str, Any], Any]:
    """Try every usable official template's logo against the frame; return the
    (template_detail, pose) whose logo scored best."""
    best: tuple[dict[str, Any], Any] | None = None
    tried = 0
    diagnostics: list[str] = []
    for summary in list_candidates(None, None):
        template = get_template(summary["id"])
        if template is None:
            continue
        if not template.get("logo_bbox") or not template.get("logo_offsets"):
            continue
        try:
            _, logo_crop = _load_template_assets(template)
        except LogoAnchorError:
            continue
        tried += 1
        stats: dict[str, float] = {}
        pose = detect_logo(frame, logo_crop, stats=stats)
        if pose is None:
            diagnostics.append(_format_stats(template["id"], stats))
        elif best is None or pose.score > best[1].score:
            best = (template, pose)
    if tried == 0:
        raise LogoAnchorError(409, "no template has logo_bbox + button_offsets + image")
    if best is None:
        raise LogoAnchorError(
            404,
            "no template logo detected in the frame; "
            f"need sift>={LOGO_SIFT_MIN_MATCHES}, "
            f"or sift>={LOGO_SIFT_SOFT_MATCHES} with refined>={LOGO_SOFT_MIN_REFINED}, "
            "or refined>=0.75 — " + "; ".join(diagnostics),
        )
    return best


def _format_stats(template_id: str, stats: dict[str, float]) -> str:
    corr = stats.get("best_corr")
    sift = stats.get("best_sift")
    refined = stats.get("best_refined")
    parts = [
        f"corr={corr:.2f}" if corr is not None else "no correlation peak",
        f"sift={sift:.0f}" if sift is not None else None,
        f"refined={refined:.2f}" if refined is not None else None,
    ]
    return f"{template_id}: " + " ".join(p for p in parts if p)


def _run_match(
    template: dict[str, Any],
    template_img: np.ndarray,
    pose: LogoPose | None,
    frame: np.ndarray,
) -> dict[str, Any]:
    logo_bbox = template["logo_bbox"]
    buttons = {
        b["button_id"]: b["bbox_template_coordinates"] for b in template["buttons"]
    }
    result = match_with_logo_anchor(
        frame_points=frame,
        template_points=template_img,
        buttons=buttons,
        logo_offsets=template["logo_offsets"],
        logo_pose=pose,
        template_logo_width=float(logo_bbox["width"]),
        template_logo_center=(
            logo_bbox["x"] + logo_bbox["width"] / 2.0,
            logo_bbox["y"] + logo_bbox["height"] / 2.0,
        ),
    )
    result["template_id"] = template["id"]
    result["logo_bbox_template"] = logo_bbox
    return result


def _detect_via_brand(frame: np.ndarray) -> dict[str, Any] | None:
    """Brand-first flow: SIFT gallery names the brand, brand filters the
    candidate templates, ORB homography inliers pick the exact model.
    Returns the best match result, or None when no brand logo is found
    (caller falls back to per-template logo search)."""
    gallery = _brand_gallery()
    if not gallery:
        return None
    brand_match = detect_brand(frame, gallery)
    if brand_match is None or brand_match.pose is None:
        return None
    gallery_logo = next(g for g in gallery if g.brand == brand_match.brand)
    gallery_logo_w = float(gallery_logo.image.shape[1])

    best: dict[str, Any] | None = None
    for summary in list_candidates(brand_match.brand, None):
        template = get_template(summary["id"])
        if template is None:
            continue
        if not template.get("logo_bbox") or not template.get("logo_offsets"):
            continue
        try:
            template_img, _ = _load_template_assets(template)
        except LogoAnchorError:
            continue
        # Gallery pose scale is relative to the gallery image width; re-express
        # it against this template's logo_bbox width.
        detected_logo_w = gallery_logo_w * brand_match.pose.scale
        pose = LogoPose(
            center_x=brand_match.pose.center_x,
            center_y=brand_match.pose.center_y,
            scale=detected_logo_w / float(template["logo_bbox"]["width"]),
            rotation=brand_match.pose.rotation,
            score=brand_match.pose.score,
        )
        result = _run_match(template, template_img, pose, frame)
        if _better(result, best):
            best = result
    if best is None:
        return None
    best["brand"] = brand_match.brand
    best["brand_matches"] = brand_match.match_count
    best["brand_inliers"] = brand_match.inliers
    return best


def _better(candidate: dict[str, Any], best: dict[str, Any] | None) -> bool:
    """Rank template matches: accepted homography beats logo-similarity,
    then more ORB inliers, then higher match score."""

    def key(r: dict[str, Any]) -> tuple:
        return (
            1 if r["tier"] == "HOMOGRAPHY_REFINED" else 0,
            r.get("inlier_count") or 0,
            r.get("match_score") or 0.0,
        )

    if not candidate["accepted"]:
        return False
    return best is None or key(candidate) > key(best)


def run_logo_anchor(template_id: str | None, frame_bytes: bytes) -> dict[str, Any]:
    """
    Execute the computer vision pipeline to align a frame against templates.

    If a template_id is specified, directly matches against that template's logo.
    Otherwise, executes the brand-first algorithm: detects the brand from the logo gallery,
    filters templates of that brand, and selects the best matching template by comparing
    homography inlier scores.

    Args:
        template_id (str | None): Explicit template ID, or None for auto-detection.
        frame_bytes (bytes): The raw uploaded camera image file bytes.

    Raises:
        LogoAnchorError: 503 if OpenCV is missing, 400 if image cannot be decoded,
            404 if no logo/template is matched, or 409 if template is misconfigured.

    Returns:
        dict[str, Any]: Match outcome with projections, match tier, and score metrics.
    """
    if cv2 is None:
        raise LogoAnchorError(503, "OpenCV is not available on the server")

    frame = cv2.imdecode(np.frombuffer(frame_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise LogoAnchorError(400, "cannot decode uploaded image")

    if template_id:
        template = get_template(template_id)
        if template is None:
            raise LogoAnchorError(404, f"template not found: {template_id}")
        if not template.get("logo_bbox"):
            raise LogoAnchorError(409, "template has no logo_bbox")
        if not template.get("logo_offsets"):
            raise LogoAnchorError(409, "no button_offsets; run compute_logo_offsets.py first")
        template_img, logo_crop = _load_template_assets(template)
        pose = detect_logo(frame, logo_crop)
        return _run_match(template, template_img, pose, frame)

    # Brand-first (new algo); falls back to per-template logo search when the
    # gallery is empty or no brand logo is found in the frame.
    brand_result = _detect_via_brand(frame)
    if brand_result is not None:
        return brand_result
    template, pose = _detect_best_template(frame)
    template_img, _ = _load_template_assets(template)
    return _run_match(template, template_img, pose, frame)
