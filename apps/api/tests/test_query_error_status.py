from __future__ import annotations

import pytest

from app.services import guidance_service


def test_llm_failure_returns_502(client, monkeypatch):
    def boom(self, user_query, template):
        raise guidance_service.LLMProviderError("provider down")

    monkeypatch.setattr(guidance_service.LLMService, "generate", boom)
    response = client.post(
        "/api/query",
        json={
            "template_id": "template_toshiba_washer_panel_v1",
            "user_query_text": "Lam sao de giat nhanh?",
        },
    )
    assert response.status_code == 502
    assert response.json()["detail"]["recovery_action"] == "try_again"
