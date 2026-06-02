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
