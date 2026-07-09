from __future__ import annotations

import json

import pytest

from scripts.label_pipeline.extract import PageSource, extract_manual, write_manual_text
from scripts.label_pipeline.gemini_client import GeminiError


class FakeClient:
    def __init__(self, replies=None, error=None):
        self.replies = list(replies or [])
        self.error = error
        self.calls = 0

    def generate_json(self, prompt, *, image=None, mime_type="image/png", cache_salt=b""):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.replies.pop(0)


def test_a_page_with_a_text_layer_is_not_sent_to_gemini():
    pages = [PageSource(1, "Nhấn Micro Power để chọn công suất." * 3, None)]
    client = FakeClient()
    result = extract_manual(pages, client=client)
    assert result[0]["mode"] == "text_layer"
    assert "Micro Power" in result[0]["text"]
    assert client.calls == 0


def test_a_page_below_the_threshold_is_ocred():
    pages = [PageSource(9, "  \n ", b"scan-bytes")]
    client = FakeClient(replies=[{"text": "Nút Start bắt đầu nấu."}])
    result = extract_manual(pages, client=client)
    assert result[0] == {"page": 9, "mode": "gemini_ocr", "text": "Nút Start bắt đầu nấu."}
    assert client.calls == 1


def test_the_threshold_is_the_character_count_of_the_stripped_text():
    # 39 characters -> OCR; 40 -> text layer. Whitespace does not count.
    client = FakeClient(replies=[{"text": "ocr"}])
    assert extract_manual([PageSource(1, "a" * 39, b"img")], client=client)[0]["mode"] == "gemini_ocr"
    assert extract_manual([PageSource(1, "a" * 40, b"img")], client=FakeClient())[0]["mode"] == "text_layer"


def test_a_scanned_page_with_no_embedded_image_records_an_error():
    # pypdf cannot rasterize; a scan page normally carries one full-page image.
    pages = [PageSource(11, "", None)]
    result = extract_manual(pages, client=FakeClient())
    assert result[0]["mode"] == "gemini_ocr"
    assert result[0]["text"] is None
    assert "no embedded image" in result[0]["error"]


def test_a_failed_page_does_not_fail_the_stage():
    pages = [
        PageSource(1, "a" * 50, None),
        PageSource(2, "", b"img"),
        PageSource(3, "b" * 50, None),
    ]
    client = FakeClient(error=GeminiError("429 after 5 attempts"))
    result = extract_manual(pages, client=client)
    assert [p["page"] for p in result] == [1, 2, 3]
    assert result[1]["text"] is None
    assert result[1]["error"] == "429 after 5 attempts"
    assert result[2]["text"].startswith("b")


def test_an_ocr_reply_without_a_text_key_is_recorded_as_an_error():
    pages = [PageSource(4, "", b"img")]
    client = FakeClient(replies=[{"pages": ["wrong shape"]}])
    result = extract_manual(pages, client=client)
    assert result[0]["text"] is None
    assert "missing 'text'" in result[0]["error"]


def test_write_manual_text_records_the_source_path(tmp_path, monkeypatch):
    import scripts.label_pipeline.extract as extract_module

    monkeypatch.setattr(
        extract_module, "read_pdf", lambda _path: [PageSource(1, "x" * 50, None)]
    )
    out = tmp_path / "manual_text.json"
    written = write_manual_text(tmp_path / "m.pdf", out, client=FakeClient())

    on_disk = json.loads(out.read_text(encoding="utf-8"))
    assert on_disk == written
    assert on_disk["source"].endswith("m.pdf")
    assert on_disk["pages"][0]["mode"] == "text_layer"


def test_write_manual_text_refuses_an_empty_pdf(tmp_path, monkeypatch):
    import scripts.label_pipeline.extract as extract_module

    monkeypatch.setattr(extract_module, "read_pdf", lambda _path: [])
    with pytest.raises(ValueError, match="no pages"):
        write_manual_text(tmp_path / "m.pdf", tmp_path / "o.json", client=FakeClient())
