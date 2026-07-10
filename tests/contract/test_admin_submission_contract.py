from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SPEC = yaml.safe_load((ROOT / "apps" / "api" / "openapi.yaml").read_text(encoding="utf-8"))

HEADERS = {"X-Admin-Token": "test-token"}


def test_the_contract_declares_the_submission_body_as_json():
    body = SPEC["paths"]["/api/submissions"]["post"]["requestBody"]["content"]
    assert list(body) == ["application/json"]


def test_the_contract_declares_the_image_upload():
    body = SPEC["paths"]["/api/submissions/image"]["post"]["requestBody"]["content"]
    assert list(body) == ["multipart/form-data"]


def test_every_admin_path_requires_the_token():
    admin = {p: v for p, v in SPEC["paths"].items() if p.startswith("/api/admin")}
    assert admin
    for path, operations in admin.items():
        for method, operation in operations.items():
            assert operation.get("security") == [{"AdminToken": []}], f"{method} {path}"


def test_the_summary_fields_match_what_the_endpoint_returns(client):
    client.post(
        "/api/submissions",
        json={
            "brand": "Panasonic",
            "appliance_type": "microwave",
            "image_url": "data/submissions/abc.png",
            "proposed_labels_json": {"buttons": [{"button_id": "1"}]},
        },
    )
    row = client.get("/api/admin/submissions", headers=HEADERS).json()[0]
    required = SPEC["components"]["schemas"]["SubmissionSummary"]["required"]
    assert set(required) <= set(row)
