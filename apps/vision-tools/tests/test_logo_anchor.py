from __future__ import annotations

import numpy as np
import pytest

from scripts.logo_anchor import (
    LogoPose,
    compute_button_offsets,
    project_offsets,
    similarity_matrix,
)
from scripts.logo_anchor_match import (
    TIER_HOMOGRAPHY,
    TIER_LOGO,
    TIER_REJECTED,
    match_with_logo_anchor,
)

LOGO = {"x": 100.0, "y": 50.0, "width": 200.0, "height": 80.0}
BUTTONS = {
    "start": {"x": 400.0, "y": 300.0, "width": 60.0, "height": 40.0},
    "stop": {"x": 500.0, "y": 300.0, "width": 60.0, "height": 40.0},
}


def test_offsets_are_logo_normalized():
    offsets = compute_button_offsets(LOGO, BUTTONS)
    # start center (430, 320), logo center (200, 90), logo width 200
    assert offsets["start"]["dx"] == pytest.approx((430 - 200) / 200)
    assert offsets["start"]["dy"] == pytest.approx((320 - 90) / 200)
    assert offsets["start"]["dw"] == pytest.approx(60 / 200)
    assert offsets["start"]["dh"] == pytest.approx(40 / 200)


def test_offsets_reject_zero_width_logo():
    with pytest.raises(ValueError):
        compute_button_offsets({"x": 0, "y": 0, "width": 0, "height": 10}, BUTTONS)


def test_identity_pose_reprojects_original_positions():
    offsets = compute_button_offsets(LOGO, BUTTONS)
    pose = LogoPose(center_x=200.0, center_y=90.0, scale=1.0, rotation=0.0, score=1.0)
    projected = project_offsets(offsets, pose, LOGO["width"])
    corners = projected["start"]
    assert corners[0]["x"] == pytest.approx(400.0)
    assert corners[0]["y"] == pytest.approx(300.0)
    assert corners[2]["x"] == pytest.approx(460.0)
    assert corners[2]["y"] == pytest.approx(340.0)


def test_scaled_translated_pose_tracks_buttons():
    offsets = compute_button_offsets(LOGO, BUTTONS)
    # Frame is the template scaled 0.5x then shifted (+30, +20).
    pose = LogoPose(center_x=200 * 0.5 + 30, center_y=90 * 0.5 + 20, scale=0.5, rotation=0.0, score=0.9)
    projected = project_offsets(offsets, pose, LOGO["width"])
    corners = projected["stop"]
    assert corners[0]["x"] == pytest.approx(500 * 0.5 + 30)
    assert corners[0]["y"] == pytest.approx(300 * 0.5 + 20)


def test_rotated_pose_rotates_offsets():
    offsets = {"b": {"dx": 1.0, "dy": 0.0, "dw": 0.0, "dh": 0.0}}
    pose = LogoPose(center_x=0.0, center_y=0.0, scale=1.0, rotation=np.pi / 2, score=1.0)
    projected = project_offsets(offsets, pose, 100.0)
    # 90deg CCW: (100, 0) -> (0, 100)
    assert projected["b"][0]["x"] == pytest.approx(0.0, abs=1e-9)
    assert projected["b"][0]["y"] == pytest.approx(100.0)


def test_similarity_matrix_is_affine():
    pose = LogoPose(center_x=10.0, center_y=20.0, scale=2.0, rotation=0.3, score=1.0)
    m = similarity_matrix(pose, 50.0)
    assert m[2, 0] == 0.0 and m[2, 1] == 0.0 and m[2, 2] == 1.0


def _grid_points(shift: float = 0.0) -> np.ndarray:
    xs, ys = np.meshgrid(np.arange(5) * 40.0, np.arange(5) * 40.0)
    pts = np.column_stack([xs.ravel(), ys.ravel()])
    return pts + shift


def test_tier_homography_when_features_match():
    template_pts = _grid_points()
    frame_pts = _grid_points()  # identity: homography must pass
    result = match_with_logo_anchor(
        frame_points=frame_pts,
        template_points=template_pts,
        buttons=BUTTONS,
        logo_offsets=compute_button_offsets(LOGO, BUTTONS),
        logo_pose=LogoPose(200.0, 90.0, 1.0, 0.0, 0.95),
        template_logo_width=LOGO["width"],
    )
    assert result["tier"] == TIER_HOMOGRAPHY
    assert result["accepted"] is True
    assert set(result["projected_buttons"]) == {"start", "stop"}
    assert result["coarse_buttons"]  # coarse still reported for debugging


def test_tier_logo_when_homography_fails_but_logo_found():
    template_pts = _grid_points()
    rng = np.random.default_rng(7)
    frame_pts = rng.uniform(0, 500, size=(25, 2))  # garbage: homography rejected
    pose = LogoPose(center_x=130.0, center_y=65.0, scale=0.5, rotation=0.0, score=0.8)
    result = match_with_logo_anchor(
        frame_points=frame_pts,
        template_points=template_pts,
        buttons=BUTTONS,
        logo_offsets=compute_button_offsets(LOGO, BUTTONS),
        logo_pose=pose,
        template_logo_width=LOGO["width"],
    )
    assert result["tier"] == TIER_LOGO
    assert result["accepted"] is True
    assert result["projected_buttons"] == result["coarse_buttons"]
    # coarse projection follows the pose, not the frame corners
    start = result["projected_buttons"]["start"]
    assert start[0]["x"] == pytest.approx(130 + (400 - 200) * 0.5)
    assert start[0]["y"] == pytest.approx(65 + (300 - 90) * 0.5)


def test_tier_rejected_without_logo_or_homography():
    template_pts = _grid_points()
    rng = np.random.default_rng(11)
    frame_pts = rng.uniform(0, 500, size=(25, 2))
    result = match_with_logo_anchor(
        frame_points=frame_pts,
        template_points=template_pts,
        buttons=BUTTONS,
        logo_offsets=compute_button_offsets(LOGO, BUTTONS),
        logo_pose=None,
        template_logo_width=LOGO["width"],
    )
    assert result["tier"] == TIER_REJECTED
    assert result["accepted"] is False
    assert result["projected_buttons"] == {}
    assert result["failure_reason"] is not None
