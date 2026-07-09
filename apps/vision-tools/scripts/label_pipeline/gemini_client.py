"""The only module in the label pipeline that touches the network.

Every call is cached by content hash, so re-running the pipeline after editing a QC
rule costs zero requests. The cache key includes a hash of the prompt, which means an
edited prompt cannot silently read an entry written by the old one.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CACHE_DIR = ROOT / ".cache" / "label_pipeline"
DEFAULT_MODEL = "gemini-3.5-flash"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _is_retryable(status: int) -> bool:
    return status == 429 or 500 <= status < 600


# (url, payload) -> (status_code, body). Injected so tests never open a socket.
Transport = Callable[[str, dict[str, Any]], tuple[int, dict[str, Any]]]


class GeminiError(RuntimeError):
    pass


def load_api_key() -> str:
    """GEMINI_API_KEY from the environment, else from the repo .env."""
    key = os.getenv("GEMINI_API_KEY")
    if key:
        return key
    env_path = ROOT / ".env"
    if env_path.exists():
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("GEMINI_API_KEY=") and not line.startswith("#"):
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                if value:
                    return value
    raise GeminiError("GEMINI_API_KEY is not set; put it in .env or the environment")


def _httpx_transport(url: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    import httpx

    response = httpx.post(url, json=payload, timeout=120.0)
    try:
        body = response.json()
    except ValueError:
        body = {"error": {"message": response.text[:500]}}
    return response.status_code, body


class GeminiClient:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_MODEL,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        transport: Transport | None = None,
        max_retries: int = 5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.cache_dir = Path(cache_dir)
        self.transport = transport or _httpx_transport
        self.max_retries = max_retries
        self.sleep = sleep

    def prompt_version(self, prompt: str) -> str:
        return "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]

    def _cache_path(self, prompt: str, image: bytes | None, cache_salt: bytes) -> Path:
        # The api key is deliberately absent: it is a credential, not an input, and two
        # developers with different keys should share a cache.
        digest = hashlib.sha256()
        digest.update(self.model.encode("utf-8"))
        digest.update(b"\0")
        digest.update(self.prompt_version(prompt).encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(b"\0no-image" if image is None else image).digest())
        digest.update(b"\0")
        digest.update(cache_salt)
        return self.cache_dir / f"{digest.hexdigest()}.json"

    def generate_json(
        self,
        prompt: str,
        *,
        image: bytes | None = None,
        mime_type: str = "image/png",
        cache_salt: bytes = b"",
    ) -> dict[str, Any]:
        cache_path = self._cache_path(prompt, image, cache_salt)
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))

        parts: list[dict[str, Any]] = [{"text": prompt}]
        if image is not None:
            parts.append(
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": base64.b64encode(image).decode("ascii"),
                    }
                }
            )
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {"response_mime_type": "application/json"},
        }
        url = ENDPOINT.format(model=self.model) + f"?key={self.api_key}"

        body = self._post_with_retry(url, payload)
        parsed = _parse_json_content(_extract_text(body))
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(parsed, ensure_ascii=False), encoding="utf-8")
        return parsed

    def _post_with_retry(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        last_status = 0
        for attempt in range(self.max_retries):
            status, body = self.transport(url, payload)
            if status == 200:
                return body
            if not _is_retryable(status):
                message = body.get("error", {}).get("message", "")
                raise GeminiError(f"Gemini HTTP {status}: {message}")
            last_status = status
            if attempt < self.max_retries - 1:
                self.sleep(2.0**attempt)
        raise GeminiError(f"Gemini HTTP {last_status} after {self.max_retries} attempts")


def _extract_text(body: dict[str, Any]) -> Any:
    try:
        return body["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise GeminiError(f"Gemini response missing text part: {body}") from exc


def _parse_json_content(content: Any) -> dict[str, Any]:
    # Mirrors _parse_json_content in apps/api/app/services/llm_service.py. An
    # unparseable response is written into the error and never retried blindly: the
    # model refusing is not a transient fault.
    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        raise GeminiError("Gemini returned non-JSON content")
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GeminiError(f"Gemini returned invalid JSON: {text[:500]}") from exc
    if not isinstance(parsed, dict):
        raise GeminiError("Gemini JSON root must be an object")
    return parsed
