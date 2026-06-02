from __future__ import annotations

import numpy as np
import pytest

from scripts.load_inputs import synthetic_panel_points
from scripts.offline_match import match_and_project


def test_offline_match_projects_button():
    template_points = synthetic_panel_points()
    frame_points = template_points + np.array([10.0, 20.0])
    result = match_and_project(
        template_points,
        frame_points,
        {"quick_wash": {"x": 210, "y": 145, "width": 85, "height": 50}},
    )
    assert result["accepted"]
    assert result["projected_buttons"]["quick_wash"][0]["x"] == pytest.approx(220.0)
    assert result["projected_buttons"]["quick_wash"][0]["y"] == pytest.approx(165.0)
