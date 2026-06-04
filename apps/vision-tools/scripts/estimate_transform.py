from __future__ import annotations

import numpy as np

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover - environment dependent
    cv2 = None


def estimate_affine(template_points: np.ndarray, frame_points: np.ndarray) -> np.ndarray:
    if len(template_points) < 3:
        raise ValueError("at least 3 points are required")
    src = np.column_stack([template_points, np.ones(len(template_points))])
    matrix, *_ = np.linalg.lstsq(src, frame_points, rcond=None)
    affine = np.eye(3)
    affine[:2, :] = matrix.T
    return affine


def estimate_homography(template_points: np.ndarray, frame_points: np.ndarray) -> np.ndarray:
    matrix, _ = estimate_homography_with_inliers(template_points, frame_points)
    return matrix


def estimate_homography_with_inliers(
    template_points: np.ndarray,
    frame_points: np.ndarray,
    *,
    ransac_reprojection_threshold: float = 5.0,
) -> tuple[np.ndarray, np.ndarray]:
    if len(template_points) < 4:
        return estimate_affine(template_points, frame_points), np.ones(len(template_points), dtype=bool)
    if cv2 is not None:
        matrix, mask = cv2.findHomography(
            np.asarray(template_points, dtype=np.float32),
            np.asarray(frame_points, dtype=np.float32),
            cv2.RANSAC,
            ransac_reprojection_threshold,
        )
        if matrix is not None and mask is not None:
            return matrix.astype(float), mask.ravel().astype(bool)
    rows = []
    for (x, y), (u, v) in zip(template_points, frame_points, strict=True):
        rows.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        rows.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    _, _, vh = np.linalg.svd(np.asarray(rows, dtype=float))
    h = vh[-1].reshape(3, 3)
    if abs(h[2, 2]) < 1e-9:
        return estimate_affine(template_points, frame_points), np.ones(len(template_points), dtype=bool)
    return h / h[2, 2], np.ones(len(template_points), dtype=bool)


def transform_points(points: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    hom = np.column_stack([points, np.ones(len(points))])
    out = hom @ matrix.T
    return out[:, :2] / out[:, 2:3]
