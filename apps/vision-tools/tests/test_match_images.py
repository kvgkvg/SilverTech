from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from scripts.match_images import match_images

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(name: str) -> np.ndarray:
    img = cv2.imread(str(FIXTURES / name), cv2.IMREAD_GRAYSCALE)
    assert img is not None, f"missing fixture {name}"
    return img


def test_match_accepts_warped_copy_and_projects_button():
    template = _load("panel_template.png")
    frame = _load("panel_frame.png")
    buttons = {"start": {"x": 60, "y": 40, "width": 110, "height": 90}}
    result = match_images(template, frame, buttons)
    assert result["accepted"] is True
    assert result["reprojection_error"] < 3.0
    poly = result["projected_buttons"]["start"]
    assert len(poly) == 4
    # All 4 projected corners land inside the 600x400 frame (sane homography).
    for corner in poly:
        assert 0 <= corner["x"] <= 600
        assert 0 <= corner["y"] <= 400
    # Projected box keeps roughly its size (warp is mild: ~scale 1.05 + 6deg).
    width = abs(poly[1]["x"] - poly[0]["x"])
    assert 80 < width < 160


def test_match_rejects_unrelated_noise():
    template = _load("panel_template.png")
    rng = np.random.default_rng(7)
    noise = rng.integers(0, 255, size=template.shape, dtype=np.uint8)
    result = match_images(template, noise, {"start": {"x": 0, "y": 0, "width": 5, "height": 5}})
    assert result["accepted"] is False
    assert result["failure_reason"] is not None
    assert result["projected_buttons"] == {}
