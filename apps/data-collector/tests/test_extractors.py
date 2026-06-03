from __future__ import annotations

from pathlib import Path

from src.crawl.extractors import extract_bing_candidates

FIXTURE = Path(__file__).parent / "fixtures" / "bing_sample.html"


def test_extracts_image_and_source_urls():
    html = FIXTURE.read_text()
    results = extract_bing_candidates(html)
    assert len(results) == 2
    first = results[0]
    assert first["image_url"] == "https://img.example.com/lg-panel.jpg"
    assert first["source_url"] == "https://shop.example.com/lg-washer"
    assert first["alt_text"] == "LG washing machine control panel"
    assert first["page_title"] == "LG Washer Panel"


def test_ignores_anchors_without_m_attribute():
    html = FIXTURE.read_text()
    results = extract_bing_candidates(html)
    assert all(r["image_url"].startswith("http") for r in results)
