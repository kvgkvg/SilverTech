from __future__ import annotations

from typing import Any

import numpy as np

from scripts.estimate_transform import transform_points


def bbox_to_points(bbox: dict[str, float]) -> np.ndarray:
    x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
    return np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], dtype=float)


def project_bbox(bbox: dict[str, float], matrix: np.ndarray) -> list[dict[str, float]]:
    projected = transform_points(bbox_to_points(bbox), matrix)
    return [{"x": float(x), "y": float(y)} for x, y in projected]


def project_buttons(buttons: dict[str, dict[str, Any]], matrix: np.ndarray) -> dict[str, list[dict[str, float]]]:
    return {button_id: project_bbox(bbox, matrix) for button_id, bbox in buttons.items()}
