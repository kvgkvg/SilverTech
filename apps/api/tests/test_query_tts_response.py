from __future__ import annotations

from app.services import guidance_service


class FakeTTSService:
    def synthesize(self, text: str) -> str:
        return f"/data/tts/fake-{len(text)}.mp3"


def test_guidance_includes_audio_url_for_validated_steps(client, monkeypatch):
    monkeypatch.setattr(guidance_service, "TTSService", FakeTTSService)

    guidance = guidance_service.create_guidance(
        "template_toshiba_washer_panel_v1",
        "Lam sao de giat nhanh?",
    )

    step = guidance["steps"][0]
    assert step["button_id"] == "quick_wash"
    assert step["audio_url"] == f"/data/tts/fake-{len(step['instruction_vi'])}.mp3"
