from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _engine():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def run_ocr(path: Path) -> list[str]:
    """Return OCR text lines for an image. Empty list if nothing/failure."""
    try:
        result, _ = _engine()(str(path))
    except Exception as exc:  # noqa: BLE001 - OCR must never crash the pipeline
        print(f"[ocr] FAILED path={path}: {exc}")
        return []
    if not result:
        return []
    # RapidOCR returns [[box, text, score], ...]
    return [line[1] for line in result if len(line) >= 2 and line[1]]
