from __future__ import annotations

from io import BytesIO

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")


def test_match_endpoint_rejects_unknown_frame(client):
    # Random noise should not match any seeded template.
    rng = np.random.default_rng(1)
    noise = rng.integers(0, 255, size=(400, 600), dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", noise)
    assert ok
    response = client.post(
        "/api/vision/match",
        files={"file": ("frame.jpg", BytesIO(buf.tobytes()), "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is False
    assert body["recovery_action"] == "rescan"
    assert body["projected_buttons"] == []
