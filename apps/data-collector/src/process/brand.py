from __future__ import annotations

from typing import Optional

KNOWN_BRANDS = [
    "lg", "samsung", "panasonic", "daikin", "sony", "toshiba",
    "electrolux", "sharp", "aqua", "midea", "hitachi",
    "mitsubishi", "whirlpool", "bosch", "philips",
]


def _canonical(brand: str) -> str:
    return "LG" if brand == "lg" else brand.title()


def detect_brand(ocr_text: list[str]) -> tuple[Optional[str], bool]:
    """Return (brand, has_visible_logo) from OCR text lines via substring match."""
    joined = " ".join(ocr_text).lower()
    for brand in KNOWN_BRANDS:
        if brand in joined:
            return _canonical(brand), True
    return None, False
