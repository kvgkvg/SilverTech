from __future__ import annotations

import numpy as np

from scripts.offline_match import match_and_project


def test_offline_match_rejects_too_few_points():
    result = match_and_project(
        np.array([[0.0, 0.0], [1.0, 1.0]]),
        np.array([[10.0, 10.0], [11.0, 11.0]]),
        {"start_pause": {"x": 0, "y": 0, "width": 10, "height": 10}},
    )
    assert not result["accepted"]
    assert result["failure_reason"] == "low_confidence"
