# PanelLens Data Collector — Slice 1 Design

**Date:** 2026-06-03
**Status:** Approved (design), pending implementation plan
**Parent project:** SilverTech (elderly-first appliance panel assistant)

## Context

SilverTech matches a live camera frame of an appliance control panel to a reviewed
template, then returns step-by-step Vietnamese guidance where every step references a
validated `button_id`. The matching is logo-guided template matching. Today
`data/templates/` holds only text placeholders — there are no real panel images, and no
device manuals for the planned manual-RAG layer.

The data collector exists to fill that gap: gather real images of appliance control
panels and remote controls (preferring ones where the brand/logo is visible) plus, in
later slices, map each image to a device manual. This document specifies **Slice 1
only**: discovery → download → OCR → review gallery. Heavy ML stages are deferred.

### Why slice first

The full pipeline (spec §20 of the source brief) has seven phases. Building all of them
before seeing real collected data risks tuning a CLIP panel filter and dedup logic on
top of bad upstream data. Slice 1 produces ~500 real candidates and an HTML review
gallery so we can measure discovery precision *before* investing in the ML stages. This
matches the source brief's own advice: "do 500–1000 first, review, then scale."

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Discovery (query → URLs) | Scrape image-search result HTML | No paid API. Pipeline entry point the source brief omitted. |
| Search engine | Bing Images (default, configurable) | Less aggressive bot-blocking than Google. |
| Render | Playwright | Image search pages are JS-heavy and lazy-load. |
| Placement | `apps/data-collector/` in SilverTech monorepo | Output feeds `data/` directly; same conda env; spec-kit workflow. |
| OCR engine | RapidOCR (onnxruntime) | pip-only, no paddlepaddle install pain in shared env; accuracy fine for brand keywords. |
| Scope | Slice 1 = crawl → download → validate → OCR → gallery | Validate precision before heavy ML. |
| pHash | Computed in Slice 1 | Cheap; lets Slice 2 dedup reuse it without re-reading images. |

## Architecture

### Data flow

```
data/seeds/ (brands.json, device_types.json)
  → 01 generate queries   → data/collected/queries.jsonl
  → 02 crawl image search → data/collected/candidates.jsonl   (Playwright, Bing Images HTML)
  → 03 download + validate→ data/collected/raw/images/ , download_report.json
  → 04 OCR + brand detect → data/collected/metadata_slice1.jsonl
  → gallery               → data/collected/gallery.html
```

Each stage reads the previous stage's file and is independently re-runnable. Crawl
writes candidates *before* any download, so a download failure never forces a re-crawl.

### Directory layout

```
apps/data-collector/
  pyproject.toml          # own deps (playwright, httpx, rapidocr-onnxruntime, pillow, imagehash, jinja2, pydantic-settings)
  README.md
  .env.example
  src/
    config.py             # env load, paths, thresholds (pydantic-settings)
    seeds.py              # brands × device_types × templates → query records
    crawl/
      image_search.py     # query → candidate image+source URLs (Playwright)
      extractors.py       # parse result DOM → img_url, source_url, alt, title
    download/
      downloader.py       # async fetch with retries (httpx)
    process/
      validator.py        # size / aspect / decode reject (Pillow)
      ocr.py              # RapidOCR wrapper → list[str]
      brand.py            # OCR text → brand, has_visible_logo
    report/
      gallery.py          # metadata → HTML grid (jinja2)
  scripts/
    01_generate_queries.py
    02_crawl_candidates.py
    03_download_images.py
    04_process_images.py
    build_gallery.py
  tests/

data/                     # in SilverTech repo root, NOT inside apps/
  seeds/
    brands.json
    device_types.json
  collected/              # all Slice 1 output (kept separate from reviewed data/templates/)
    queries.jsonl
    candidates.jsonl
    raw/
      pages/              # saved result HTML for debugging
      images/
    metadata_slice1.jsonl
    gallery.html
    download_report.json
    rejected/
      too_small/
      bad_aspect/
      decode_fail/
      download_fail/
    unverified/           # downloaded + valid but OCR found no brand (NOT deleted)
```

`data/collected/` is deliberately separate from `data/templates/`. Templates are
human-reviewed, official, and consumed by the runtime; collected data is raw and
unreviewed. Nothing in Slice 1 writes to `data/templates/`.

## Module responsibilities

- **config.py** — loads `.env`, exposes typed settings: data dir, engine name, user
  agent, timeouts, concurrency, min width/height/file-size, aspect bounds. One source of
  truth for thresholds.
- **seeds.py** — given `brands.json` and `device_types.json`, expands query templates
  (`{brand} {device_query}`, `... manual`, `... buttons`, `... front panel`) into query
  records `{query, brand, device_type, intent}`. Pure function, easy to test.
- **crawl/image_search.py** — for each query, drives Playwright to the configured engine,
  scrolls to lazy-load N results, hands the DOM to `extractors.py`, writes
  `candidates.jsonl`. Saves raw HTML to `raw/pages/`. Polite per-request delay. Never
  crashes the run on a single bad page — logs and continues.
- **crawl/extractors.py** — engine-specific DOM parsing → `image_url`, `source_url`,
  `alt_text`, `page_title`. Isolated so a layout change touches one file.
- **download/downloader.py** — async httpx fetch with bounded concurrency and retries.
  Writes images to `raw/images/`, records success/failure with reason in
  `download_report.json`.
- **process/validator.py** — opens each image with Pillow; rejects on width < MIN,
  height < MIN, file size < MIN, decode failure, or aspect ratio outside [1:6, 6:1].
  Moves rejects into the matching `rejected/<reason>/` folder.
- **process/ocr.py** — thin RapidOCR wrapper: image path → `list[str]` of text lines.
  Engine swap (to PaddleOCR) is a later concern; the interface stays.
- **process/brand.py** — lowercases joined OCR text, substring-matches against
  `KNOWN_BRANDS`, returns brand (canonical-cased) or None, sets `has_visible_logo`.
  No-brand images go to `unverified/`, not deleted — stylized logos are often missed by
  OCR.
- **report/gallery.py** — renders `metadata_slice1.jsonl` into a single self-contained
  `gallery.html` grid. The precision-review surface.

## Data schema — `metadata_slice1.jsonl`

```jsonc
{
  "candidate_id": "cand_000001",
  "query": "LG washing machine control panel",
  "brand_hint": "LG",
  "device_type_hint": "washing_machine",
  "source_url": "https://example.com/...",
  "image_url": "https://example.com/....jpg",
  "alt_text": "...",
  "page_title": "...",
  "image_path": "data/collected/raw/images/cand_000001.jpg",
  "image_width": 1024,
  "image_height": 768,
  "file_size": 184320,
  "ocr_text": ["LG", "Cotton", "Temp", "Spin", "Start/Pause"],
  "ocr_joined": "LG Cotton Temp Spin Start/Pause",
  "brand": "LG",
  "brand_source": "ocr",
  "has_visible_logo": true,
  "phash": "f0f0c3a1b2d4e8f9",
  "status": "ocr_done",          // candidate | downloaded | validated | ocr_done | rejected
  "reject_reason": null,          // null | too_small | bad_aspect | decode_fail | download_fail
  "license": "unknown",
  "usage_note": "research/internal only unless license verified",
  "created_at": "2026-06-03T00:00:00Z"
}
```

Deferred fields (Slice 2+): `panel_score`, CLIP embedding, `model`, `model_source`,
`panel_type`, `brand_confidence`, `manual_url`, `manual_local_path`, `manual_md_path`,
`manual_status`, the resized `processed/images/` copy, and the final `id`/`image_path`
under `processed/`.

## Error handling

- A single failing search page or image URL never aborts the run; it is logged and
  skipped. `02` and `03` always finish and report counts.
- Download failures recorded with HTTP status / exception in `download_report.json`.
- Validation rejects are moved (not deleted) into `rejected/<reason>/` so they can be
  inspected.
- If the search engine blocks the crawler (empty results across queries), that surfaces
  as a near-empty `candidates.jsonl` and an empty gallery — a fast, visible failure that
  tells us to fix discovery before anything else.

## Testing

- **seeds.py** — unit test: known brands × devices expands to expected query count and
  shape.
- **extractors.py** — unit test against a saved sample result HTML fixture (no live
  network) → expected image/source URLs.
- **validator.py** — unit tests with synthetic Pillow images: too-small, bad-aspect,
  corrupt, and a valid image each routed correctly.
- **brand.py** — unit test: OCR text with/without each known brand → correct brand and
  `has_visible_logo`.
- **downloader.py** — test with a mocked httpx transport: success, 404, timeout each
  recorded correctly.
- Live crawl is **not** unit-tested (network + anti-bot make it nondeterministic); it is
  validated manually via the gallery.

## Acceptance criteria (Slice 1)

1. `candidates.jsonl` has ≥ 500 records; each has `source_url` and at least one of
   `brand_hint` / `device_type_hint`.
2. Crawl does not crash on a bad page; failed URLs/pages are logged.
3. Download success ≥ 60% of candidates; `download_report.json` lists reasons for
   failures.
4. Every downloaded, validated image has `ocr_text` and `has_visible_logo` set; brand
   filled from OCR when present.
5. No-brand images are in `unverified/`, not deleted.
6. `gallery.html` renders all processed images plus rejects, showing image, query,
   brand, OCR text, source_url, and reject reason.

## Legal / source note

Every record stores `source_url`, `image_url`, `license` (default `"unknown"`), and
`usage_note` (`"research/internal only unless license verified"`). The dataset is for
internal SilverTech research/demo use; it is not to be published until licenses are
verified. Image-search scraping is fragile and ToS-gray — kept low-volume and
single-purpose.

## Out of scope (later slices)

- Slice 2: CLIP/SigLIP zero-shot panel/remote filter (`panel_score`).
- Slice 3: deduplication (pHash distance + CLIP cosine), resize into `processed/images/`,
  final `metadata.jsonl`.
- Slice 4: manual discovery, PDF download, markdown conversion, `manual_status`.

Each later slice gets its own spec → plan → implementation cycle.
