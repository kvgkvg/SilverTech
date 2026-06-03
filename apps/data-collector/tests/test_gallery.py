from __future__ import annotations

from src.report.gallery import render_gallery


def test_render_includes_record_fields():
    records = [
        {
            "candidate_id": "cand_000001",
            "query": "LG washing machine control panel",
            "image_path": "data/collected/raw/images/cand_000001.jpg",
            "brand": "LG",
            "device_type_hint": "washing_machine",
            "ocr_joined": "LG Cotton Spin",
            "source_url": "https://shop.example.com/lg",
            "status": "ocr_done",
            "reject_reason": None,
        }
    ]
    html = render_gallery(records)
    assert "cand_000001" in html
    assert "LG washing machine control panel" in html
    assert "LG Cotton Spin" in html
    assert "https://shop.example.com/lg" in html
    assert "<img" in html


def test_render_shows_reject_reason():
    records = [
        {
            "candidate_id": "cand_000002",
            "query": "Samsung washer",
            "image_path": "x.jpg",
            "brand": None,
            "device_type_hint": "washing_machine",
            "ocr_joined": "",
            "source_url": "https://x",
            "status": "rejected",
            "reject_reason": "too_small",
        }
    ]
    html = render_gallery(records)
    assert "too_small" in html
