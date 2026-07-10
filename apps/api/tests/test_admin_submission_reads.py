from __future__ import annotations

HEADERS = {"X-Admin-Token": "test-token"}

LABELS = {"device": {}, "template": {}, "buttons": [{"button_id": "1"}]}


def _submit(client, brand="Panasonic"):
    return client.post(
        "/api/submissions",
        json={
            "brand": brand,
            "appliance_type": "microwave",
            "image_url": "data/submissions/abc.png",
            "proposed_labels_json": LABELS,
        },
    ).json()["submission_id"]


def test_listing_requires_the_token(client):
    assert client.get("/api/admin/submissions").status_code == 401


def test_it_lists_pending_submissions(client):
    submission_id = _submit(client)
    rows = client.get("/api/admin/submissions?status=pending", headers=HEADERS).json()
    assert [r["id"] for r in rows] == [submission_id]
    assert rows[0]["brand"] == "Panasonic"
    assert rows[0]["image_url"] == "data/submissions/abc.png"


def test_the_list_is_not_filtered_without_a_status(client):
    _submit(client)
    assert len(client.get("/api/admin/submissions", headers=HEADERS).json()) == 1


def test_a_reviewed_submission_leaves_the_pending_list(client):
    submission_id = _submit(client)
    client.post(
        f"/api/admin/submissions/{submission_id}/review",
        json={"decision": "reject"},
        headers=HEADERS,
    )
    assert client.get("/api/admin/submissions?status=pending", headers=HEADERS).json() == []


def test_the_detail_returns_decoded_labels(client):
    submission_id = _submit(client)
    body = client.get(f"/api/admin/submissions/{submission_id}", headers=HEADERS).json()
    assert body["id"] == submission_id
    assert body["proposed_labels_json"] == LABELS
    assert body["status"] == "pending"


def test_an_unknown_submission_is_a_404(client):
    assert client.get("/api/admin/submissions/nope", headers=HEADERS).status_code == 404
