from __future__ import annotations

import numpy as np

from scripts.confidence import compute_reprojection_error, score_confidence
from scripts.estimate_transform import estimate_homography_with_inliers, transform_points
from scripts.extract_orb_features import extract_orb_features
from scripts.match_descriptors import filter_good_matches, match_descriptors
from scripts.project_buttons import project_buttons


def match_and_project(
    template_points: np.ndarray,
    frame_points: np.ndarray,
    buttons: dict,
    *,
    min_inliers: int = 4,
    min_inlier_ratio: float = 0.5,
    max_reprojection_error: float = 5.0,
) -> dict:
    tpl_pts, tpl_desc = extract_orb_features(template_points)
    frm_pts, frm_desc = extract_orb_features(frame_points)
    matches = filter_good_matches(match_descriptors(tpl_desc, frm_desc, max_distance=500.0), 500.0)
    if len(matches) < 3:
        return {"accepted": False, "failure_reason": "low_confidence", "projected_buttons": {}}
    src = np.array([tpl_pts[i] for i, _, _ in matches], dtype=float)
    dst = np.array([frm_pts[j] for _, j, _ in matches], dtype=float)
    matrix, inlier_mask = estimate_homography_with_inliers(src, dst)
    inlier_src = src[inlier_mask]
    inlier_dst = dst[inlier_mask]
    projected = transform_points(inlier_src, matrix)
    error = compute_reprojection_error(projected, inlier_dst)
    confidence = score_confidence(
        match_count=len(inlier_src),
        total_keypoints=len(tpl_pts),
        reprojection_error=error,
        min_inliers=min_inliers,
        min_inlier_ratio=min_inlier_ratio,
        max_reprojection_error=max_reprojection_error,
    )
    if not confidence.accepted:
        return {
            "accepted": False,
            "failure_reason": confidence.failure_reason,
            "match_score": confidence.match_score,
            "inlier_count": confidence.inlier_count,
            "inlier_ratio": confidence.inlier_ratio,
            "reprojection_error": confidence.reprojection_error,
            "projected_buttons": {},
        }
    return {
        "accepted": True,
        "failure_reason": None,
        "match_score": confidence.match_score,
        "inlier_count": confidence.inlier_count,
        "inlier_ratio": confidence.inlier_ratio,
        "reprojection_error": confidence.reprojection_error,
        "matrix": matrix.tolist(),
        "inlier_frame_points": inlier_dst.tolist(),
        "projected_buttons": project_buttons(buttons, matrix),
    }
