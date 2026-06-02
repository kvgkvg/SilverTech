from __future__ import annotations


def sift_available() -> bool:
    try:
        import cv2  # type: ignore

        return hasattr(cv2, "SIFT_create")
    except Exception:
        return False
