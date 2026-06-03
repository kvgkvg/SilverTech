from __future__ import annotations

from pathlib import Path

from PIL import Image


def validate_image(path: Path, min_w: int, min_h: int, min_kb: int, max_aspect: float) -> dict:
    """Validate a downloaded image. Returns {ok, reason, width, height}."""
    try:
        size_kb = path.stat().st_size / 1024
        with Image.open(path) as img:
            img.verify()
        with Image.open(path) as img:
            width, height = img.size
    except Exception:  # noqa: BLE001 - any decode/IO error means reject
        return {"ok": False, "reason": "decode_fail", "width": None, "height": None}

    if size_kb < min_kb:
        return {"ok": False, "reason": "too_small", "width": width, "height": height}
    if width < min_w or height < min_h:
        return {"ok": False, "reason": "too_small", "width": width, "height": height}
    long_side, short_side = max(width, height), min(width, height)
    if short_side == 0 or long_side / short_side > max_aspect:
        return {"ok": False, "reason": "bad_aspect", "width": width, "height": height}
    return {"ok": True, "reason": None, "width": width, "height": height}
