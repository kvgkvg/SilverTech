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
