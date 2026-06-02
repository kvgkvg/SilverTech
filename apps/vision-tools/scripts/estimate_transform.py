from __future__ import annotations

import numpy as np


def estimate_affine(template_points: np.ndarray, frame_points: np.ndarray) -> np.ndarray:
    if len(template_points) < 3:
        raise ValueError("at least 3 points are required")
    src = np.column_stack([template_points, np.ones(len(template_points))])
    matrix, *_ = np.linalg.lstsq(src, frame_points, rcond=None)
    affine = np.eye(3)
    affine[:2, :] = matrix.T
    return affine


def estimate_homography(template_points: np.ndarray, frame_points: np.ndarray) -> np.ndarray:
    if len(template_points) < 4:
        return estimate_affine(template_points, frame_points)
    rows = []
    for (x, y), (u, v) in zip(template_points, frame_points, strict=True):
        rows.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        rows.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    _, _, vh = np.linalg.svd(np.asarray(rows, dtype=float))
    h = vh[-1].reshape(3, 3)
    if abs(h[2, 2]) < 1e-9:
        return estimate_affine(template_points, frame_points)
    return h / h[2, 2]


def transform_points(points: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    hom = np.column_stack([points, np.ones(len(points))])
    out = hom @ matrix.T
    return out[:, :2] / out[:, 2:3]
