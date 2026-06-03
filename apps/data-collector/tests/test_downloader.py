from __future__ import annotations

import httpx

from src.download.downloader import download_one


def _client_returning(status: int, body: bytes = b"") -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=body)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_download_one_success(tmp_path):
    client = _client_returning(200, b"\xff\xd8\xff\xe0imagebytes")
    dest = tmp_path / "img.jpg"
    result = download_one(client, "https://x/img.jpg", dest)
    assert result["ok"] is True
    assert dest.exists()
    assert result["file_size"] == len(b"\xff\xd8\xff\xe0imagebytes")


def test_download_one_http_error(tmp_path):
    client = _client_returning(404)
    dest = tmp_path / "img.jpg"
    result = download_one(client, "https://x/missing.jpg", dest)
    assert result["ok"] is False
    assert result["reason"] == "http_404"
    assert not dest.exists()
