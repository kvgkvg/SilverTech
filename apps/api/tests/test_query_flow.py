from __future__ import annotations


def test_query_returns_valid_button_id(client):
    response = client.post(
        "/api/query",
        json={
            "template_id": "template_toshiba_washer_panel_v1",
            "user_query_text": "Lam sao de giat nhanh?",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["steps"][0]["button_id"] == "quick_wash"


def test_temperature_query_uses_ac_button(client):
    response = client.post(
        "/api/query",
        json={
            "template_id": "template_daikin_ac_remote_v1",
            "user_query_text": "Toi muon chinh nhiet do dieu hoa",
        },
    )
    assert response.status_code == 200
    assert response.json()["steps"][0]["button_id"] == "temp_up"


def test_irrelevant_query_refused_without_steps(client):
    response = client.post(
        "/api/query",
        json={
            "template_id": "template_toshiba_washer_panel_v1",
            "user_query_text": "Hom nay troi dep khong?",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "out_of_scope"
    assert data["steps"] == []
    assert data["safety_note"]
