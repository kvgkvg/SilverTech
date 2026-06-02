from __future__ import annotations


def test_submission_contract(client):
    response = client.post(
        "/api/submissions",
        json={
            "brand": "Panasonic",
            "appliance_type": "washing_machine",
            "image_url": "data/templates/pending_panel.jpg",
            "proposed_labels_json": {"buttons": [{"button_id": "start_pause"}]},
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
