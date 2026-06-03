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


def test_substring_does_not_false_positive():
    # "Aquastop" must not match brand "Aqua"; "Sharpen" must not match "Sharp".
    brand, has_logo = detect_brand(["Aquastop", "Sharpen rinse", "lglobal"])
    assert brand is None
    assert has_logo is False


def test_brand_matches_among_other_tokens():
    brand, has_logo = detect_brand(["LG 6081", "Heavy", "Cotton"])
    assert brand == "LG"
    assert has_logo is True
