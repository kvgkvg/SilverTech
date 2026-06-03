from __future__ import annotations

from src.process.brand import detect_brand

def test_detects_lg_uppercase():
    brand, has_logo = detect_brand(["LG", "Cotton", "Spin"])
    assert brand == "LG"
    assert has_logo is True


def test_detects_samsung_titlecase():
    brand, has_logo = detect_brand(["samsung", "eco bubble"])
    assert brand == "Samsung"
    assert has_logo is True


def test_no_brand_found():
    brand, has_logo = detect_brand(["Start", "Pause", "Temp"])
    assert brand is None
    assert has_logo is False
