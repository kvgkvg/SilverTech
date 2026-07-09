from __future__ import annotations

import pytest

from scripts.label_pipeline.geometry import bbox_area, center, iou, to_bbox

# Both gold images, deliberately non-square: a transposed axis cannot survive both.
PANASONIC = {"width": 5712, "height": 4284}
ELECTROLUX = {"width": 2560, "height": 810}


def test_box_2d_maps_y_first_not_x_first():
    # box_2d is [ymin, xmin, ymax, xmax] normalized to 0..1000.
    box = to_bbox([100, 500, 200, 750], **PANASONIC)
    assert box["x"] == 2856
    assert box["y"] == 428
    assert box["width"] == 1428
    assert box["height"] == 429


def test_box_2d_on_a_wide_image_exposes_a_transposed_axis():
    # 3.2:1. Reading box_2d as [xmin, ymin, ...] would put x at 256, not 1280.
    box = to_bbox([100, 500, 200, 750], **ELECTROLUX)
    assert box == {"x": 1280, "y": 81, "width": 640, "height": 81}


def test_corners_are_rounded_before_they_are_subtracted():
    # ymin 100 -> 428.4 -> 428;  ymax 200 -> 856.8 -> 857;  height = 857 - 428 = 429.
    # Rounding the difference instead gives round(428.4) = 428. The edge moves a pixel.
    box = to_bbox([100, 0, 200, 1000], **PANASONIC)
    assert box["height"] == 429


def test_exact_halves_round_up_not_to_even():
    # 500/1000 * 1 == 0.5 exactly. Python's round() is banker's rounding and would
    # return 0 here; _round_half_up returns 1. Only an exact half tells them apart,
    # so the assertion has to land on one.
    box = to_bbox([0, 0, 1000, 500], width=1, height=1)
    assert box["width"] == 1
    assert box["height"] == 1


def test_a_full_frame_box_spans_the_whole_image():
    box = to_bbox([0, 0, 1000, 1000], **ELECTROLUX)
    assert box == {"x": 0, "y": 0, "width": 2560, "height": 810}


def test_to_bbox_rejects_a_box_that_is_not_four_numbers():
    with pytest.raises(ValueError, match="four"):
        to_bbox([1, 2, 3], width=100, height=100)


def test_identical_boxes_have_iou_one():
    box = {"x": 10, "y": 10, "width": 20, "height": 20}
    assert iou(box, box) == pytest.approx(1.0)


def test_disjoint_boxes_have_iou_zero():
    a = {"x": 0, "y": 0, "width": 10, "height": 10}
    b = {"x": 100, "y": 100, "width": 10, "height": 10}
    assert iou(a, b) == 0.0


def test_boxes_that_only_touch_at_an_edge_have_iou_zero():
    a = {"x": 0, "y": 0, "width": 10, "height": 10}
    b = {"x": 10, "y": 0, "width": 10, "height": 10}
    assert iou(a, b) == 0.0


def test_half_overlap_has_iou_one_third():
    # intersection 50, union 150.
    a = {"x": 0, "y": 0, "width": 10, "height": 10}
    b = {"x": 5, "y": 0, "width": 10, "height": 10}
    assert iou(a, b) == pytest.approx(1 / 3)


def test_a_degenerate_box_has_iou_zero_and_never_divides_by_zero():
    a = {"x": 0, "y": 0, "width": 0, "height": 10}
    b = {"x": 0, "y": 0, "width": 10, "height": 10}
    assert iou(a, b) == 0.0


def test_bbox_area_and_center():
    box = {"x": 10, "y": 20, "width": 30, "height": 40}
    assert bbox_area(box) == 1200
    assert center(box) == (25.0, 40.0)
