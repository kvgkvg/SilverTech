from __future__ import annotations

import re
from typing import Optional

KNOWN_BRANDS = [
    "lg", "samsung", "panasonic", "daikin", "sony", "toshiba",
    "electrolux", "sharp", "aqua", "midea", "hitachi",
    "mitsubishi", "whirlpool", "bosch", "philips",
]

# Word-boundary patterns so brand tokens only match whole words. A plain substring
# match misfires on incidental OCR text ("Aquastop" -> Aqua, "Sharpen" -> Sharp,
# "lglobal" -> LG), which would pollute the brand precision signal this stage exists
# to measure.
_PATTERNS = [(brand, re.compile(rf"\b{re.escape(brand)}\b", re.IGNORECASE)) for brand in KNOWN_BRANDS]


def _canonical(brand: str) -> str:
    return "LG" if brand == "lg" else brand.title()


def detect_brand(ocr_text: list[str]) -> tuple[Optional[str], bool]:
    """Return (brand, has_visible_logo) from OCR text lines via word-boundary match."""
    joined = " ".join(ocr_text)
    for brand, pattern in _PATTERNS:
        if pattern.search(joined):
            return _canonical(brand), True
    return None, False
