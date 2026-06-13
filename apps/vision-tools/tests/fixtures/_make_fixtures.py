from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent


def _panel() -> np.ndarray:
    rng = np.random.default_rng(42)
    img = (rng.integers(0, 60, size=(400, 600), dtype=np.uint8))
    # High-contrast "buttons": filled rectangles with borders => ORB corners.
    boxes = [(60, 40), (260, 40), (460, 40), (160, 220), (360, 220)]
    for (x, y) in boxes:
        cv2.rectangle(img, (x, y), (x + 110, y + 90), 255, -1)
        cv2.rectangle(img, (x + 12, y + 12), (x + 98, y + 78), 0, 4)
    return img


def main() -> None:
    template = _panel()
    cv2.imwrite(str(HERE / "panel_template.png"), template)
    h, w = template.shape
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), 6.0, 1.05)
    matrix[0, 2] += 18
    matrix[1, 2] += 12
    frame = cv2.warpAffine(template, matrix, (w, h), borderValue=20)
    cv2.imwrite(str(HERE / "panel_frame.png"), frame)


if __name__ == "__main__":
    main()
