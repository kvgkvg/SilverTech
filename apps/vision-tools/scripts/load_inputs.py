from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


def load_button_coordinates(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def synthetic_panel_points(offset: tuple[float, float] = (0.0, 0.0)) -> np.ndarray:
    base = np.array(
        [
            [20, 10],
            [140, 12],
            [210, 145],
            [315, 145],
            [500, 150],
            [590, 205],
            [40, 220],
            [620, 30],
        ],
        dtype=float,
    )
    return base + np.array(offset, dtype=float)
