from __future__ import annotations

import numpy as np


def match_descriptors(template_desc: np.ndarray, frame_desc: np.ndarray, max_distance: float = 5.0) -> list[tuple[int, int, float]]:
    matches: list[tuple[int, int, float]] = []
    for i, desc in enumerate(template_desc.astype(float)):
        distances = np.linalg.norm(frame_desc.astype(float) - desc, axis=1)
        j = int(np.argmin(distances))
        distance = float(distances[j])
        if distance <= max_distance:
            matches.append((i, j, distance))
    return matches


def filter_good_matches(matches: list[tuple[int, int, float]], max_distance: float = 5.0) -> list[tuple[int, int, float]]:
    return [m for m in matches if m[2] <= max_distance]


def match_descriptors_hamming(
    query_desc: "np.ndarray",
    train_desc: "np.ndarray",
    *,
    ratio: float = 0.75,
) -> list[tuple[int, int, float]]:
    """Match binary (ORB) descriptors with BFMatcher(NORM_HAMMING) + Lowe ratio.

    Returns (query_index, train_index, distance) for surviving matches.
    """
    import cv2

    if query_desc is None or train_desc is None:
        return []
    if len(query_desc) == 0 or len(train_desc) < 2:
        return []
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    knn = bf.knnMatch(
        np.asarray(query_desc, dtype=np.uint8),
        np.asarray(train_desc, dtype=np.uint8),
        k=2,
    )
    good: list[tuple[int, int, float]] = []
    for pair in knn:
        if len(pair) < 2:
            continue
        best, second = pair[0], pair[1]
        if best.distance <= ratio * second.distance:
            good.append((best.queryIdx, best.trainIdx, float(best.distance)))
    return good
