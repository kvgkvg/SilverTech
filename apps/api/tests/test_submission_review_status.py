from __future__ import annotations


def test_submission_is_pending_and_not_candidate(client):
    response = client.post(
        "/api/submissions",
        json={
            "brand": "Toshiba",
            "appliance_type": "washing_machine",
            "image_url": "data/templates/new_panel.jpg",
            "proposed_labels_json": {"buttons": []},
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending"

    candidates = client.post(
        "/api/vision/candidates",
        json={"brand": "Toshiba", "appliance_type": "washing_machine"},
    ).json()["candidates"]
    assert all(candidate["status"] == "official" for candidate in candidates)
