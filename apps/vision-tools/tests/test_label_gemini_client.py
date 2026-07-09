from __future__ import annotations

import json

import pytest

from scripts.label_pipeline import gemini_client
from scripts.label_pipeline.gemini_client import GeminiClient, GeminiError, ROOT, load_api_key


def ok_body(payload: object) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]}


class FakeTransport:
    """Records every call and replays a scripted list of (status, body) responses."""

    def __init__(self, responses: list[tuple[int, dict]]):
        self.responses = list(responses)
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, url: str, payload: dict) -> tuple[int, dict]:
        self.calls.append((url, payload))
        if not self.responses:
            raise AssertionError("transport called more times than the test scripted")
        return self.responses.pop(0)


def make_client(tmp_path, responses, **kwargs) -> tuple[GeminiClient, FakeTransport]:
    transport = FakeTransport(responses)
    client = GeminiClient(
        api_key="test-key",
        cache_dir=tmp_path / "cache",
        transport=transport,
        sleep=lambda _seconds: None,
        **kwargs,
    )
    return client, transport


def test_a_json_response_is_parsed(tmp_path):
    client, _ = make_client(tmp_path, [(200, ok_body({"detections": []}))])
    assert client.generate_json("find the buttons") == {"detections": []}


def test_a_fenced_json_response_is_unwrapped(tmp_path):
    fenced = {"candidates": [{"content": {"parts": [{"text": '```json\n{"a": 1}\n```'}]}}]}
    client, _ = make_client(tmp_path, [(200, fenced)])
    assert client.generate_json("p") == {"a": 1}


def test_a_second_identical_call_is_served_from_cache(tmp_path):
    client, transport = make_client(tmp_path, [(200, ok_body({"a": 1}))])
    assert client.generate_json("same prompt") == {"a": 1}
    assert client.generate_json("same prompt") == {"a": 1}
    assert len(transport.calls) == 1  # the second call never left the process


def test_editing_the_prompt_misses_the_cache(tmp_path):
    # prompt_version is the hash of the prompt, so an edited prompt cannot read a
    # stale entry written by the old one.
    client, transport = make_client(tmp_path, [(200, ok_body({"a": 1})), (200, ok_body({"a": 2}))])
    assert client.generate_json("prompt one") == {"a": 1}
    assert client.generate_json("prompt two") == {"a": 2}
    assert len(transport.calls) == 2


def test_changing_the_image_misses_the_cache(tmp_path):
    client, transport = make_client(tmp_path, [(200, ok_body({"a": 1})), (200, ok_body({"a": 2}))])
    client.generate_json("p", image=b"first-image")
    client.generate_json("p", image=b"second-image")
    assert len(transport.calls) == 2


def test_no_image_and_empty_bytes_image_do_not_share_a_cache_entry(tmp_path):
    # image=None sends no inline_data part; image=b"" sends one with empty data.
    # Different payloads must not collide on the same cache key.
    client, transport = make_client(tmp_path, [(200, ok_body({"a": 1})), (200, ok_body({"a": 2}))])
    assert client.generate_json("p", image=None) == {"a": 1}
    assert client.generate_json("p", image=b"") == {"a": 2}
    assert len(transport.calls) == 2


def test_changing_the_model_misses_the_cache(tmp_path):
    responses = [(200, ok_body({"a": 1})), (200, ok_body({"a": 2}))]
    transport = FakeTransport(responses)
    shared_cache = tmp_path / "cache"
    common = {"api_key": "k", "cache_dir": shared_cache, "transport": transport,
              "sleep": lambda _s: None}
    GeminiClient(model="model-a", **common).generate_json("p")
    GeminiClient(model="model-b", **common).generate_json("p")
    assert len(transport.calls) == 2


def test_a_429_is_retried_and_then_succeeds(tmp_path):
    client, transport = make_client(tmp_path, [(429, {}), (429, {}), (200, ok_body({"a": 1}))])
    assert client.generate_json("p") == {"a": 1}
    assert len(transport.calls) == 3


def test_a_503_is_retried(tmp_path):
    client, transport = make_client(tmp_path, [(503, {}), (200, ok_body({"a": 1}))])
    assert client.generate_json("p") == {"a": 1}
    assert len(transport.calls) == 2


def test_a_501_is_retried(tmp_path):
    # 501 is a 5xx not in the old hardcoded RETRY_STATUS set; the predicate must
    # still treat it as retryable.
    client, transport = make_client(tmp_path, [(501, {}), (200, ok_body({"a": 1}))])
    assert client.generate_json("p") == {"a": 1}
    assert len(transport.calls) == 2


def test_backoff_grows_between_retries(tmp_path):
    delays: list[float] = []
    transport = FakeTransport([(429, {}), (429, {}), (200, ok_body({"a": 1}))])
    client = GeminiClient(api_key="k", cache_dir=tmp_path / "c", transport=transport,
                          sleep=delays.append)
    client.generate_json("p")
    assert delays == [1.0, 2.0]


def test_retries_are_bounded(tmp_path):
    client, transport = make_client(tmp_path, [(429, {})] * 3, max_retries=3)
    with pytest.raises(GeminiError, match="429 after 3 attempts"):
        client.generate_json("p")
    assert len(transport.calls) == 3


def test_a_400_is_not_retried(tmp_path):
    # A malformed request will be malformed the second time too.
    client, transport = make_client(tmp_path, [(400, {"error": {"message": "bad model"}})])
    with pytest.raises(GeminiError, match="400"):
        client.generate_json("p")
    assert len(transport.calls) == 1


def test_unparseable_json_raises_and_is_not_retried(tmp_path):
    body = {"candidates": [{"content": {"parts": [{"text": "sorry, I cannot do that"}]}}]}
    client, transport = make_client(tmp_path, [(200, body)])
    with pytest.raises(GeminiError, match="invalid JSON"):
        client.generate_json("p")
    assert len(transport.calls) == 1


def test_a_failed_call_is_not_cached(tmp_path):
    client, transport = make_client(tmp_path, [(400, {}), (200, ok_body({"a": 1}))])
    with pytest.raises(GeminiError):
        client.generate_json("p")
    assert client.generate_json("p") == {"a": 1}
    assert len(transport.calls) == 2


def test_the_api_key_never_reaches_the_cache_key(tmp_path):
    # Two clients, different keys, same prompt: the second must hit the cache.
    transport = FakeTransport([(200, ok_body({"a": 1}))])
    common = {"cache_dir": tmp_path / "c", "transport": transport, "sleep": lambda _s: None}
    GeminiClient(api_key="key-one", **common).generate_json("p")
    GeminiClient(api_key="key-two", **common).generate_json("p")
    assert len(transport.calls) == 1


def test_prompt_version_is_a_hash_of_the_prompt(tmp_path):
    client, _ = make_client(tmp_path, [])
    version = client.prompt_version("hello")
    assert version.startswith("sha256:")
    assert version == client.prompt_version("hello")
    assert version != client.prompt_version("hello ")


def test_the_image_is_sent_as_inline_base64(tmp_path):
    client, transport = make_client(tmp_path, [(200, ok_body({}))])
    client.generate_json("p", image=b"\x89PNG-bytes", mime_type="image/png")
    _url, payload = transport.calls[0]
    parts = payload["contents"][0]["parts"]
    assert parts[0] == {"text": "p"}
    assert parts[1]["inline_data"]["mime_type"] == "image/png"
    assert parts[1]["inline_data"]["data"] == "iVBORy1ieXRlcw=="


def test_root_is_the_directory_containing_apps():
    # Pins the parents[N] arithmetic in gemini_client.py. gemini_client.py lives at
    # apps/vision-tools/scripts/label_pipeline/gemini_client.py, so ROOT must climb
    # four levels to reach the repo root, not three (that lands one directory
    # shallow, inside apps/).
    assert (ROOT / "apps" / "vision-tools").is_dir()


def test_load_api_key_returns_the_env_var_when_set(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "from-environment")
    assert load_api_key() == "from-environment"


def test_load_api_key_falls_back_to_the_repo_root_env_file(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    (tmp_path / ".env").write_text("GEMINI_API_KEY=from-dot-env\n", encoding="utf-8")
    monkeypatch.setattr(gemini_client, "ROOT", tmp_path)
    assert load_api_key() == "from-dot-env"


def test_load_api_key_ignores_a_commented_out_line(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    (tmp_path / ".env").write_text("#GEMINI_API_KEY=commented-out\n", encoding="utf-8")
    monkeypatch.setattr(gemini_client, "ROOT", tmp_path)
    with pytest.raises(GeminiError, match="GEMINI_API_KEY is not set"):
        load_api_key()


def test_load_api_key_ignores_an_empty_value(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    (tmp_path / ".env").write_text("GEMINI_API_KEY=\n", encoding="utf-8")
    monkeypatch.setattr(gemini_client, "ROOT", tmp_path)
    with pytest.raises(GeminiError, match="GEMINI_API_KEY is not set"):
        load_api_key()


def test_load_api_key_raises_when_the_key_is_nowhere(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(gemini_client, "ROOT", tmp_path)
    with pytest.raises(GeminiError, match="GEMINI_API_KEY is not set"):
        load_api_key()
