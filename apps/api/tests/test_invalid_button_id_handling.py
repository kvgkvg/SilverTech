from __future__ import annotations

from app.services.guidance_service import GuidanceError, create_guidance


def test_missing_template_returns_error(client):
    try:
        create_guidance("missing", "Nut bat dau o dau?")
    except GuidanceError as exc:
        assert str(exc) == "missing_template"
    else:
        raise AssertionError("missing template should fail")


def test_query_endpoint_rejects_missing_template(client):
    response = client.post(
        "/api/query",
        json={"template_id": "missing", "user_query_text": "Nut bat dau o dau?"},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["recovery_action"] == "manual_select"
