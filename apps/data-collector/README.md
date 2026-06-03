# PanelLens Data Collector (Slice 1)

Collects appliance control-panel / remote images to feed SilverTech template + manual
data. Slice 1 = discovery → download → validate → OCR → review gallery. CLIP panel
filtering, dedup, and manual mapping are deferred to later slices.

## Install (inside `silvertech` conda env)

```bash
conda activate silvertech
cd apps/data-collector
python3 -m pip install -e .
python3 -m playwright install chromium
cp .env.example .env   # optional; defaults are fine
```

## Run the pipeline

Paths default to the repo-root `data/` dir via `COLLECTOR_DATA_DIR`.

```bash
PYTHONPATH=. COLLECTOR_DATA_DIR=../../data python3 scripts/01_generate_queries.py
PYTHONPATH=. COLLECTOR_DATA_DIR=../../data python3 scripts/02_crawl_candidates.py --limit 1000
PYTHONPATH=. COLLECTOR_DATA_DIR=../../data python3 scripts/03_download_images.py
PYTHONPATH=. COLLECTOR_DATA_DIR=../../data python3 scripts/04_process_images.py
PYTHONPATH=. COLLECTOR_DATA_DIR=../../data python3 scripts/build_gallery.py
```

Then open `data/collected/gallery.html` to review precision.

## Output

- `data/collected/candidates.jsonl` — discovered image+source URLs
- `data/collected/raw/images/` — downloaded images
- `data/collected/metadata_slice1.jsonl` — per-image OCR/brand/phash
- `data/collected/gallery.html` — review grid
- `data/collected/rejected/<reason>/` — too_small, bad_aspect, decode_fail, download_fail
- `data/collected/unverified/` — valid images where OCR found no brand (kept, not deleted)

## Rejection reasons

`too_small` (below min width/height/size), `bad_aspect` (ratio > 6:1), `decode_fail`
(corrupt/unreadable), `download_fail` (HTTP/network error).

## Legal / source note

Every record stores `source_url`, `image_url`, `license` (default `unknown`), and
`usage_note`. Internal research/demo use only; do not publish until licenses are
verified. Image-search scraping is fragile and ToS-gray — keep volume low.

## Tests

```bash
PYTHONPATH=. pytest -q tests
```
