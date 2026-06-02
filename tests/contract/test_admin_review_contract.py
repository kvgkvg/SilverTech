from __future__ import annotations


def test_admin_review_contract(client):
    submission = client.post(
        "/api/submissions",
        json={
            "brand": "Panasonic",
            "appliance_type": "washing_machine",
            "image_url": "data/templates/pending_panel_2.jpg",
            "proposed_labels_json": {"buttons": [{"button_id": "start_pause"}]},
        },
    ).json()
    response = client.post(
        f"/api/admin/submissions/{submission['submission_id']}/review",
        json={"decision": "reject", "reviewer_note": "Needs clearer panel image"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
