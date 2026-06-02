from __future__ import annotations

import numpy as np

from scripts.project_buttons import project_bbox


def test_project_bbox_translation():
    matrix = np.array([[1, 0, 10], [0, 1, 20], [0, 0, 1]], dtype=float)
    points = project_bbox({"x": 1, "y": 2, "width": 3, "height": 4}, matrix)
    assert points[0] == {"x": 11.0, "y": 22.0}
    assert points[2] == {"x": 14.0, "y": 26.0}
