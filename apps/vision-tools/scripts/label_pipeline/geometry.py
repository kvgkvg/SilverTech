"""Pure geometry for the label pipeline. No I/O, no network, imports nothing local."""

from __future__ import annotations

import math
from collections.abc import Sequence

Bbox = dict[str, int]


def _round_half_up(value: float) -> int:
    # round() is banker's rounding: round(0.5) == 0 but round(1.5) == 2. A box edge
    # landing on an exact half would then move by a pixel depending on its parity.
    return int(math.floor(value + 0.5))


def to_bbox(box_2d: Sequence[int], *, width: int, height: int) -> Bbox:
    """Convert Gemini's [ymin, xmin, ymax, xmax] (0..1000) to absolute {x, y, width, height}.

    Two things happen here at once: the axis order is transposed, and the values are
    scaled by the image dimensions. Getting the order wrong yields boxes that look
    plausible in JSON and are wrong on the image.
    """
    if len(box_2d) != 4:
        raise ValueError(f"box_2d must be four numbers [ymin, xmin, ymax, xmax], got {box_2d!r}")
    ymin, xmin, ymax, xmax = box_2d
    x = _round_half_up(xmin / 1000 * width)
    y = _round_half_up(ymin / 1000 * height)
    return {
        "x": x,
        "y": y,
        "width": _round_half_up(xmax / 1000 * width) - x,
        "height": _round_half_up(ymax / 1000 * height) - y,
    }


def bbox_area(box: Bbox) -> int:
    return max(0, box["width"]) * max(0, box["height"])


def center(box: Bbox) -> tuple[float, float]:
    return (box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)


def iou(a: Bbox, b: Bbox) -> float:
    """Intersection over union. A degenerate box scores 0 rather than dividing by zero."""
    ax2, ay2 = a["x"] + a["width"], a["y"] + a["height"]
    bx2, by2 = b["x"] + b["width"], b["y"] + b["height"]
    overlap_w = min(ax2, bx2) - max(a["x"], b["x"])
    overlap_h = min(ay2, by2) - max(a["y"], b["y"])
    if overlap_w <= 0 or overlap_h <= 0:
        return 0.0
    intersection = overlap_w * overlap_h
    union = bbox_area(a) + bbox_area(b) - intersection
    if union <= 0:
        return 0.0
    return intersection / union
