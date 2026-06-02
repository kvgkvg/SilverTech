from __future__ import annotations


def test_template_contract(client):
    candidates = client.post(
        "/api/vision/candidates",
        json={"brand": "Toshiba", "appliance_type": "washing_machine"},
    )
    assert candidates.status_code == 200
    template_id = candidates.json()["candidates"][0]["id"]
    detail = client.get(f"/api/templates/{template_id}")
    assert detail.status_code == 200
    assert detail.json()["buttons"]
