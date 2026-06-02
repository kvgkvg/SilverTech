from __future__ import annotations


def test_guidance_contract(client):
    stt = client.post("/api/stt", content=b"mock")
    assert stt.status_code == 200
    query = client.post(
        "/api/query",
        json={
            "template_id": "template_toshiba_washer_panel_v1",
            "user_query_text": stt.json()["text"],
        },
    )
    assert query.status_code == 200
    step = query.json()["steps"][0]
    assert {"step_number", "instruction_vi", "button_id", "expected_result"}.issubset(step)
