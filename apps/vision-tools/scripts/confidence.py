from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ConfidenceResult:
    accepted: bool
    match_score: float
    inlier_count: int
    inlier_ratio: float
    reprojection_error: float
    failure_reason: str | None


def compute_reprojection_error(projected: np.ndarray, actual: np.ndarray) -> float:
    """
    Calculate the average Euclidean distance between projected points and actual points.

    Args:
        projected (np.ndarray): Projected Nx2 keypoint coordinates.
        actual (np.ndarray): Actual detected Nx2 keypoint coordinates in target frame.

    Returns:
        float: Mean reprojection error. Returns infinity if points are empty.
    """
    if len(projected) == 0:
        return float("inf")
    return float(np.mean(np.linalg.norm(projected - actual, axis=1)))


def score_confidence(
    *,
    match_count: int,
    total_keypoints: int,
    reprojection_error: float,
    min_inliers: int = 4,
    min_inlier_ratio: float = 0.5,
    max_reprojection_error: float = 5.0,
) -> ConfidenceResult:
    """
    Evaluate the quality of keypoint matching and homography projection.

    Validates minimum inlier counts, inlier ratios, and maximum average reprojection
    error thresholds. Computes a composite match score in [0, 1].

    Args:
        match_count (int): Number of RANSAC inliers.
        total_keypoints (int): Total keypoints in the template image.
        reprojection_error (float): Mean reprojection error of inliers.
        min_inliers (int, optional): Minimum required inliers. Defaults to 4.
        min_inlier_ratio (float, optional): Minimum inliers / total ratio. Defaults to 0.5.
        max_reprojection_error (float, optional): Maximum allowed error. Defaults to 5.0.

    Returns:
        ConfidenceResult: A frozen dataclass storing evaluation results and acceptance.
    """
    total = max(total_keypoints, 1)
    ratio = match_count / total
    score = max(0.0, min(1.0, ratio * (1.0 - min(reprojection_error / 50.0, 1.0))))
    reason = None
    if match_count < min_inliers:
        reason = "low_confidence"
    elif ratio < min_inlier_ratio:
        reason = "low_confidence"
    elif reprojection_error > max_reprojection_error:
        reason = "low_confidence"
    return ConfidenceResult(
        accepted=reason is None,
        match_score=score,
        inlier_count=match_count,
        inlier_ratio=ratio,
        reprojection_error=reprojection_error,
        failure_reason=reason,
    )
