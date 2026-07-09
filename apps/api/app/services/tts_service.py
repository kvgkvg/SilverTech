from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable, Protocol

from app.storage.database import ROOT


class TTSServiceError(RuntimeError):
    pass


class GTTSLike(Protocol):
    def write_to_fp(self, fp) -> None: ...


GTTSFactory = Callable[..., GTTSLike]


def _default_gtts_factory(*args, **kwargs) -> GTTSLike:
    try:
        from gtts import gTTS
    except Exception as exc:  # pragma: no cover - depends on local install
        raise TTSServiceError("gTTS is not installed") from exc
    return gTTS(*args, **kwargs)


class TTSService:
    def __init__(
        self,
        *,
        output_dir: Path | None = None,
        url_prefix: str = "/data/tts",
        gtts_factory: GTTSFactory | None = None,
        lang: str = "vi",
        slow: bool = False,
        timeout: int = 15,
    ) -> None:
        self.output_dir = output_dir or ROOT / "data" / "tts"
        self.url_prefix = url_prefix.rstrip("/")
        self.gtts_factory = gtts_factory or _default_gtts_factory
        self.lang = lang
        self.slow = slow
        self.timeout = timeout

    def synthesize(self, text: str) -> str:
        clean = " ".join(text.split())
        if not clean:
            raise TTSServiceError("TTS text is empty")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{self._digest(clean)}.mp3"
        path = self.output_dir / filename
        if path.exists():
            return f"{self.url_prefix}/{filename}"
        try:
            with path.open("wb") as fp:
                tts = self.gtts_factory(
                    clean,
                    lang=self.lang,
                    slow=self.slow,
                    lang_check=True,
                    timeout=self.timeout,
                )
                tts.write_to_fp(fp)
        except Exception as exc:
            path.unlink(missing_ok=True)
            if isinstance(exc, TTSServiceError):
                raise
            raise TTSServiceError(str(exc)) from exc
        return f"{self.url_prefix}/{filename}"

    def _digest(self, text: str) -> str:
        key = f"{self.lang}|{self.slow}|{text}".encode("utf-8")
        return hashlib.sha256(key).hexdigest()[:20]
