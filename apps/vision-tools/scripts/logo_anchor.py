from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class LogoPose:
    """Detected logo placement in a frame: center, scale, rotation."""

    center_x: float
    center_y: float
    scale: float  # detected logo width / template logo width
    rotation: float  # radians, counter-clockwise
    score: float  # detection confidence in [0, 1]


def bbox_center(bbox: dict[str, float]) -> tuple[float, float]:
    return bbox["x"] + bbox["width"] / 2.0, bbox["y"] + bbox["height"] / 2.0


def compute_button_offsets(
    logo_bbox: dict[str, float],
    buttons: dict[str, dict[str, float]],
) -> dict[str, dict[str, float]]:
    """Normalized button offsets relative to the logo anchor.

    Offsets are expressed in logo-width units so they survive any uniform
    rescaling of the frame: dx = (button_cx - logo_cx) / logo_width.
    """
    logo_w = float(logo_bbox["width"])
    if logo_w <= 0:
        raise ValueError("logo_bbox width must be positive")
    logo_cx, logo_cy = bbox_center(logo_bbox)
    offsets: dict[str, dict[str, float]] = {}
    for button_id, bbox in buttons.items():
        cx, cy = bbox_center(bbox)
        offsets[button_id] = {
            "dx": (cx - logo_cx) / logo_w,
            "dy": (cy - logo_cy) / logo_w,
            "dw": bbox["width"] / logo_w,
            "dh": bbox["height"] / logo_w,
        }
    return offsets


def similarity_matrix(pose: LogoPose, template_logo_width: float) -> np.ndarray:
    """3x3 similarity transform mapping logo-offset space into frame pixels.

    Offset space has the logo center at the origin with logo-width units;
    the transform scales by the detected logo width, rotates by the logo
    rotation, and translates to the detected logo center.
    """
    s = pose.scale * template_logo_width
    c, r = np.cos(pose.rotation), np.sin(pose.rotation)
    return np.array(
        [
            [s * c, -s * r, pose.center_x],
            [s * r, s * c, pose.center_y],
            [0.0, 0.0, 1.0],
        ]
    )


def project_offsets(
    offsets: dict[str, dict[str, float]],
    pose: LogoPose,
    template_logo_width: float,
) -> dict[str, list[dict[str, float]]]:
    """Project button offset rectangles into frame coordinates (4 corners each)."""
    matrix = similarity_matrix(pose, template_logo_width)
    projected: dict[str, list[dict[str, float]]] = {}
    for button_id, off in offsets.items():
        hw, hh = off["dw"] / 2.0, off["dh"] / 2.0
        corners = np.array(
            [
                [off["dx"] - hw, off["dy"] - hh, 1.0],
                [off["dx"] + hw, off["dy"] - hh, 1.0],
                [off["dx"] + hw, off["dy"] + hh, 1.0],
                [off["dx"] - hw, off["dy"] + hh, 1.0],
            ]
        )
        pts = corners @ matrix.T
        projected[button_id] = [{"x": float(x), "y": float(y)} for x, y, _ in pts]
    return projected


def offsets_from_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Convert button_offsets DB rows into the offsets mapping used above."""
    return {
        row["button_id"]: {
            "dx": float(row["dx"]),
            "dy": float(row["dy"]),
            "dw": float(row["dw"]),
            "dh": float(row["dh"]),
        }
        for row in rows
    }
