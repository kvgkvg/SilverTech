from __future__ import annotations

"""
Boundary and Edge-Case Integration Tests for SilverTech FastAPI Backend.

This module contains comprehensive integration tests designed to verify backend robustness 
against boundary inputs, invalid requests, and exceptional workflows. It validates 
schema compliance, proper HTTP status code returns, and database state logging constraints.
"""


def test_query_empty_body(client):
    """
    Verify that a POST request to `/api/query` with an empty body fails validation.

    Ensures that FastAPI schema validation catches the empty request and returns
    the appropriate HTTP 422 Unprocessable Entity status.

    Args:
        client: The TestClient fixture initialized with the FastAPI application.
    """
    response = client.post("/api/query", json={})
    assert response.status_code == 422


def test_query_missing_fields(client):
    """
    Verify that query requests lacking required fields are rejected by the validator.

    Args:
        client: The TestClient fixture initialized with the FastAPI application.
    """
    response = client.post("/api/query", json={"user_query_text": "Làm sao để giặt nhanh?"})
    assert response.status_code == 422


def test_query_nonexistent_template(client):
    """
    Verify that querying a nonexistent template ID yields a 404 status code.

    Ensures that the backend logic gracefully flags missing templates and returns
    the standardized error payload details.

    Args:
        client: The TestClient fixture initialized with the FastAPI application.
    """
    response = client.post(
        "/api/query",
        json={
            "template_id": "template_nonexistent_device_v1",
            "user_query_text": "Làm sao để nấu cháo?",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "missing_template"


def test_query_extremely_long_text(client):
    """
    Verify that querying with a very long string does not crash the server.

    Validates that the system safely processes large input strings and returns
    a standard query response structure without raising unhandled exceptions.

    Args:
        client: The TestClient fixture initialized with the FastAPI application.
    """
    long_query = "giặt nhanh " * 200  # 2000 characters
    response = client.post(
        "/api/query",
        json={
            "template_id": "template_toshiba_washer_panel_v1",
            "user_query_text": long_query,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "intent" in data
    assert isinstance(data["steps"], list)


def test_candidates_empty_body(client):
    """
    Verify that the candidates search endpoint rejects empty JSON bodies.

    Args:
        client: The TestClient fixture initialized with the FastAPI application.
    """
    response = client.post("/api/vision/candidates", json={})
    assert response.status_code == 422


def test_candidates_invalid_confidence(client):
    """
    Verify that the candidates endpoint enforces correct data types for confidence scores.

    The brand_confidence score must be a numeric type (float/integer); strings should be rejected.

    Args:
        client: The TestClient fixture initialized with the FastAPI application.
    """
    response = client.post(
        "/api/vision/candidates",
        json={
            "brand": "Toshiba",
            "appliance_type": "washer",
            "brand_confidence": "extremely_high",
        },
    )
    assert response.status_code == 422


def test_logo_anchor_missing_file(client):
    """
    Verify that the logo-anchor endpoint fails with 422 when the image file is omitted.

    Args:
        client: The TestClient fixture initialized with the FastAPI application.
    """
    response = client.post("/api/vision/logo-anchor", data={"template_id": "template_toshiba_washer_panel_v1"})
    assert response.status_code == 422


def test_admin_review_nonexistent(client):
    """
    Verify that reviewing a nonexistent submission returns a 404 error.

    Args:
        client: The TestClient fixture initialized with the FastAPI application.
    """
    response = client.post(
        "/api/admin/submissions/sub_nonexistent_id_9999/review",
        json={
            "decision": "accept",
            "reviewer_note": "Approved by testing script.",
        },
    )
    assert response.status_code == 404


def test_admin_review_invalid_decision(client):
    """
    Verify that the submission review endpoint rejects invalid decision states.

    Decisions must strictly be 'accept', 'edit', or 'reject'. Other strings must fail.

    Args:
        client: The TestClient fixture initialized with the FastAPI application.
    """
    response = client.post(
        "/api/admin/submissions/sub_some_id_123/review",
        json={
            "decision": "delete_all",
            "reviewer_note": "Should fail validator.",
        },
    )
    assert response.status_code == 422
