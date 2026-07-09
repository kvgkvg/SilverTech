"""Stage 1: appliance manual PDF -> manual_text.json.

A page whose text layer is too short is treated as a scan and sent to Gemini for OCR.
Both modes can occur in one document. `mode` is recorded per page because the first
question about a wrong description is always whether that page was read or OCR'd.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

from scripts.label_pipeline.gemini_client import GeminiClient, GeminiError

MIN_TEXT_LAYER_CHARS = 40

OCR_PROMPT = """You are reading one page of a household appliance manual.

Transcribe every word you can see, in the original language, preserving line breaks.
Do not translate. Do not summarise. Do not describe images.

Return JSON: {"text": "<the full transcription>"}
"""


class PageSource(NamedTuple):
    number: int
    text: str
    image: bytes | None


def read_pdf(path: Path) -> list[PageSource]:
    """The only function here that touches pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages: list[PageSource] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:  # noqa: BLE001 - a broken page must not kill the document
            text = ""
        image: bytes | None = None
        try:
            embedded = list(page.images)
        except Exception:  # noqa: BLE001
            embedded = []
        if embedded:
            # A scanned page carries one full-page image; take the largest.
            image = max((i.data for i in embedded), key=len)
        pages.append(PageSource(index, text, image))
    return pages


def extract_manual(
    pages: list[PageSource],
    *,
    client: GeminiClient,
    min_chars: int = MIN_TEXT_LAYER_CHARS,
) -> list[dict]:
    results: list[dict] = []
    for page in pages:
        stripped = page.text.strip()
        if len(stripped) >= min_chars:
            results.append({"page": page.number, "mode": "text_layer", "text": stripped})
            continue
        results.append(_ocr_page(page, client))
    return results


def _ocr_page(page: PageSource, client: GeminiClient) -> dict:
    failed = {"page": page.number, "mode": "gemini_ocr", "text": None}
    if page.image is None:
        return {**failed, "error": "no embedded image to OCR"}
    try:
        reply = client.generate_json(OCR_PROMPT, image=page.image, mime_type="image/jpeg")
    except GeminiError as exc:
        return {**failed, "error": str(exc)}
    text = reply.get("text")
    if not isinstance(text, str):
        return {**failed, "error": f"OCR reply missing 'text': {reply!r}"}
    return {"page": page.number, "mode": "gemini_ocr", "text": text}


def write_manual_text(
    pdf_path: Path,
    out_path: Path,
    *,
    client: GeminiClient,
    min_chars: int = MIN_TEXT_LAYER_CHARS,
) -> dict:
    pages = read_pdf(pdf_path)
    if not pages:
        raise ValueError(f"{pdf_path} has no pages")
    document = {
        "source": str(pdf_path),
        "pages": extract_manual(pages, client=client, min_chars=min_chars),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    return document


def manual_full_text(document: dict) -> str:
    """Every page that was read, joined. Used by describe.py and by the no_evidence rule."""
    return "\n\n".join(
        f"[page {p['page']}]\n{p['text']}" for p in document["pages"] if p.get("text")
    )
