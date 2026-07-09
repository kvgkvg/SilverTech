from __future__ import annotations

import hashlib
from pathlib import Path

from app.services.tts_service import TTSService


class FakeGTTS:
    calls: list[dict[str, object]] = []

    def __init__(
        self,
        text: str,
        *,
        lang: str,
        slow: bool,
        lang_check: bool,
        timeout: int,
    ):
        self.text = text
        FakeGTTS.calls.append(
            {
                "text": text,
                "lang": lang,
                "slow": slow,
                "lang_check": lang_check,
                "timeout": timeout,
            }
        )

    def write_to_fp(self, fp) -> None:
        fp.write(b"fake mp3 bytes")


def test_synthesizes_vietnamese_instruction_to_deterministic_mp3(tmp_path: Path):
    FakeGTTS.calls.clear()
    service = TTSService(
        output_dir=tmp_path,
        url_prefix="/data/tts",
        gtts_factory=FakeGTTS,
    )

    audio_url = service.synthesize("Nhấn nút Bắt đầu.")

    digest = hashlib.sha256("vi|False|Nhấn nút Bắt đầu.".encode("utf-8")).hexdigest()[:20]
    assert audio_url == f"/data/tts/{digest}.mp3"
    assert (tmp_path / f"{digest}.mp3").read_bytes() == b"fake mp3 bytes"
    assert FakeGTTS.calls == [
        {
            "text": "Nhấn nút Bắt đầu.",
            "lang": "vi",
            "slow": False,
            "lang_check": True,
            "timeout": 15,
        }
    ]


def test_reuses_existing_audio_file_without_resynthesizing(tmp_path: Path):
    FakeGTTS.calls.clear()
    service = TTSService(
        output_dir=tmp_path,
        url_prefix="/data/tts",
        gtts_factory=FakeGTTS,
    )

    first_url = service.synthesize("Nhấn nút Bắt đầu.")
    calls_after_first = len(FakeGTTS.calls)
    second_url = service.synthesize("Nhấn nút Bắt đầu.")

    assert second_url == first_url
    assert len(FakeGTTS.calls) == calls_after_first
