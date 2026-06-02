from __future__ import annotations


class STTService:
    def transcribe(self, audio: bytes | None, locale: str = "vi-VN") -> tuple[str, float]:
        if not audio:
            return "Làm sao để giặt nhanh?", 0.95
        return "Làm sao để giặt nhanh?", 0.90
