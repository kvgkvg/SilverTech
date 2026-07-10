# Author: Le Nguyen Khang (MSSV: 23122034) - Vision Confidence score benchmark
from __future__ import annotations

from scripts.confidence import score_confidence


def test_confidence_accepts_good_match():
    result = score_confidence(match_count=8, total_keypoints=8, reprojection_error=0.5)
    assert result.accepted
    assert result.failure_reason is None


def test_confidence_rejects_low_inliers():
    result = score_confidence(match_count=2, total_keypoints=8, reprojection_error=0.5)
    assert not result.accepted
    assert result.failure_reason == "low_confidence"
