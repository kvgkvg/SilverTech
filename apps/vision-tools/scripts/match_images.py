from __future__ import annotations

from typing import Any

import numpy as np

from scripts.confidence import compute_reprojection_error, score_confidence
from scripts.estimate_transform import estimate_homography_with_inliers, transform_points
from scripts.match_descriptors import match_descriptors_hamming
from scripts.project_buttons import project_buttons

_MIN_MATCHES = 4


def _orb_features(image: np.ndarray):
    import cv2

    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=1500)
    keypoints, descriptors = orb.detectAndCompute(gray, None)
    points = np.array([kp.pt for kp in keypoints], dtype=float)
    return points, descriptors


def _rejected(reason: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    out = {"accepted": False, "failure_reason": reason, "projected_buttons": {}}
    if extra:
        out.update(extra)
    return out


def match_images(
    template_image: np.ndarray | None,
    frame_image: np.ndarray,
    buttons: dict[str, dict[str, float]],
    *,
    template_keypoints: np.ndarray | None = None,
    template_descriptors: np.ndarray | None = None,
) -> dict[str, Any]:
    """Match a frame against a template by real ORB features and project buttons.

    `template_keypoints`/`template_descriptors` may be supplied (precomputed) to
    skip re-extracting the template every call. Result shape matches
    `offline_match.match_and_project`.
    """
    if template_keypoints is None or template_descriptors is None:
        tpl_pts, tpl_desc = _orb_features(template_image)
    else:
        tpl_pts, tpl_desc = np.asarray(template_keypoints, dtype=float), template_descriptors
    frm_pts, frm_desc = _orb_features(frame_image)

    if tpl_desc is None or frm_desc is None or len(tpl_pts) == 0 or len(frm_pts) == 0:
        return _rejected("low_confidence")

    matches = match_descriptors_hamming(tpl_desc, frm_desc, ratio=0.75)
    if len(matches) < _MIN_MATCHES:
        return _rejected("low_confidence")

    src = np.array([tpl_pts[i] for i, _, _ in matches], dtype=float)
    dst = np.array([frm_pts[j] for _, j, _ in matches], dtype=float)
    matrix, inlier_mask = estimate_homography_with_inliers(src, dst)
    inlier_src = src[inlier_mask]
    inlier_dst = dst[inlier_mask]
    if len(inlier_src) < _MIN_MATCHES:
        return _rejected("low_confidence")

    projected = transform_points(inlier_src, matrix)
    error = compute_reprojection_error(projected, inlier_dst)
    confidence = score_confidence(
        match_count=len(inlier_src),
        total_keypoints=len(tpl_pts),
        reprojection_error=error,
        # Real ORB finds ~1000 template keypoints but only ~10-15% survive
        # Lowe-ratio + RANSAC against a real frame (inlier_ratio ~0.13 observed),
        # vs synthetic arrays where total_keypoints == matched-set size. The
        # min_inliers (4) and reprojection-error (<5px) gates still reject noise
        # (0 RANSAC inliers). Re-tune on real photos in P2.
        min_inlier_ratio=0.10,
    )
    payload = {
        "match_score": confidence.match_score,
        "inlier_count": confidence.inlier_count,
        "inlier_ratio": confidence.inlier_ratio,
        "reprojection_error": confidence.reprojection_error,
    }
    if not confidence.accepted:
        return _rejected(confidence.failure_reason, payload)
    return {
        "accepted": True,
        "failure_reason": None,
        **payload,
        "matrix": matrix.tolist(),
        "projected_buttons": project_buttons(buttons, matrix),
    }
