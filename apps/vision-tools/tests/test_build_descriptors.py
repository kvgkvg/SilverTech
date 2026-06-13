from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from scripts.build_descriptors import build_descriptors, load_descriptors

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_build_and_load_roundtrip(tmp_path):
    out = tmp_path / "panel.npz"
    build_descriptors(str(FIXTURES / "panel_template.png"), str(out))
    keypoints, descriptors = load_descriptors(str(out))
    assert keypoints.shape[1] == 2
    assert len(keypoints) == len(descriptors)
    assert descriptors.dtype == np.uint8
    assert len(keypoints) > 10
