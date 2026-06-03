from __future__ import annotations

from src.seeds import generate_queries

BRANDS = ["LG", "Samsung"]
DEVICES = [
    {"device_type": "washing_machine", "queries": ["washing machine control panel"]},
    {"device_type": "tv_remote", "queries": ["TV remote control"]},
]


def test_generates_brand_device_query_product():
    queries = generate_queries(BRANDS, DEVICES)
    # 2 brands * 2 devices * 1 device-query each = 4 base queries
    assert len(queries) == 4
    texts = {q.query for q in queries}
    assert "LG washing machine control panel" in texts
    assert "Samsung TV remote control" in texts


def test_query_records_carry_brand_and_device():
    queries = generate_queries(BRANDS, DEVICES)
    lg_wm = next(q for q in queries if q.query == "LG washing machine control panel")
    assert lg_wm.brand == "LG"
    assert lg_wm.device_type == "washing_machine"
    assert lg_wm.intent == "panel_image"
