from __future__ import annotations

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from scripts.match_descriptors import match_descriptors_hamming


def test_hamming_matches_identical_descriptors():
    # Two identical descriptor sets => each row matches its own index.
    desc = np.array(
        [[0, 255, 0, 7], [255, 0, 128, 1], [3, 3, 3, 3]],
        dtype=np.uint8,
    )
    matches = match_descriptors_hamming(desc, desc.copy(), ratio=0.9)
    pairs = {(i, j) for i, j, _ in matches}
    assert (0, 0) in pairs
    assert (1, 1) in pairs


def test_hamming_ratio_test_drops_ambiguous():
    # Query row equidistant-ish to two train rows => ratio test rejects it.
    query = np.array([[0, 0]], dtype=np.uint8)
    train = np.array([[1, 0], [0, 1]], dtype=np.uint8)
    matches = match_descriptors_hamming(query, train, ratio=0.6)
    assert matches == []
