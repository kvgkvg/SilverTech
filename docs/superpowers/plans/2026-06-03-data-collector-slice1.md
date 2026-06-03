# PanelLens Data Collector Slice 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `apps/data-collector/` Slice 1: scrape image-search results for appliance control panels, download + validate images, OCR brand text, and render a review gallery — producing ~500 candidates for precision review before any ML stage.

**Architecture:** A new monorepo app with stage-per-script flow. Each stage reads the prior stage's JSONL and is independently re-runnable. Pure logic (seeds, extractors, validator, brand detect, gallery) is unit-tested with fixtures; the live Playwright crawl is driven by a thin un-unit-tested script and validated via the gallery.

**Tech Stack:** Python 3.11+, Playwright, httpx, RapidOCR (onnxruntime), Pillow, imagehash, jinja2, pydantic-settings, pytest, ruff (line-length 100).

---

## File Structure

```
apps/data-collector/
  pyproject.toml
  README.md
  .env.example
  src/
    __init__.py
    config.py             # pydantic-settings Settings + paths/thresholds
    seeds.py              # query expansion (pure)
    models.py            # dataclasses: QueryRecord, Candidate, ProcessedRecord
    crawl/
      __init__.py
      extractors.py       # parse engine result HTML -> list[Candidate] (pure)
      image_search.py     # Playwright driver (thin, not unit-tested)
    download/
      __init__.py
      downloader.py       # async httpx fetch + report
    process/
      __init__.py
      validator.py        # Pillow size/aspect/decode checks (pure-ish)
      ocr.py              # RapidOCR wrapper
      brand.py            # OCR text -> brand + has_visible_logo (pure)
    report/
      __init__.py
      gallery.py          # jinja2 HTML render (pure)
  scripts/
    01_generate_queries.py
    02_crawl_candidates.py
    03_download_images.py
    04_process_images.py
    build_gallery.py
  tests/
    fixtures/
      bing_sample.html    # saved Bing Images result snippet
    test_seeds.py
    test_extractors.py
    test_downloader.py
    test_validator.py
    test_brand.py
    test_gallery.py

data/                     # SilverTech repo root
  seeds/
    brands.json
    device_types.json
  collected/              # created at runtime by scripts
```

All work happens inside the `silvertech` conda env. Tests run with
`PYTHONPATH=apps/data-collector pytest -q apps/data-collector/tests`.

---

## Task 1: Scaffold the app (pyproject, package dirs, seeds)

**Files:**
- Create: `apps/data-collector/pyproject.toml`
- Create: `apps/data-collector/src/__init__.py` (empty)
- Create: `apps/data-collector/src/crawl/__init__.py` (empty)
- Create: `apps/data-collector/src/download/__init__.py` (empty)
- Create: `apps/data-collector/src/process/__init__.py` (empty)
- Create: `apps/data-collector/src/report/__init__.py` (empty)
- Create: `data/seeds/brands.json`
- Create: `data/seeds/device_types.json`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "silvertech-data-collector"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "playwright>=1.44",
  "httpx>=0.27",
  "rapidocr-onnxruntime>=1.3",
  "pillow>=10.0",
  "imagehash>=4.3",
  "jinja2>=3.1",
  "pydantic-settings>=2.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.ruff]
line-length = 100
```

- [ ] **Step 2: Create the five empty `__init__.py` files**

Create each of: `src/__init__.py`, `src/crawl/__init__.py`, `src/download/__init__.py`,
`src/process/__init__.py`, `src/report/__init__.py` as empty files.

- [ ] **Step 3: Write `data/seeds/brands.json`**

```json
[
  "LG", "Samsung", "Panasonic", "Daikin", "Sony", "Toshiba",
  "Electrolux", "Sharp", "Aqua", "Midea", "Hitachi",
  "Mitsubishi", "Whirlpool", "Bosch", "Philips"
]
```

- [ ] **Step 4: Write `data/seeds/device_types.json`**

```json
[
  {"device_type": "washing_machine", "queries": ["washing machine control panel", "washer control panel", "washing machine buttons", "washing machine front panel"]},
  {"device_type": "air_conditioner_remote", "queries": ["air conditioner remote control", "AC remote control buttons", "air conditioner remote display"]},
  {"device_type": "tv_remote", "queries": ["TV remote control", "television remote control buttons"]},
  {"device_type": "microwave", "queries": ["microwave control panel", "microwave buttons panel"]},
  {"device_type": "dishwasher", "queries": ["dishwasher control panel", "dishwasher buttons panel"]}
]
```

- [ ] **Step 5: Install and verify import**

Run: `cd apps/data-collector && python3 -m pip install -e . && python3 -c "import src"`
Expected: installs deps, no import error.

- [ ] **Step 6: Commit**

```bash
git add apps/data-collector/pyproject.toml apps/data-collector/src data/seeds
git commit -m "feat(data-collector): scaffold app, deps, seed data"
```

---

## Task 2: Data models

**Files:**
- Create: `apps/data-collector/src/models.py`

- [ ] **Step 1: Write `models.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class QueryRecord:
    query: str
    brand: str
    device_type: str
    intent: str = "panel_image"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Candidate:
    candidate_id: str
    query: str
    brand_hint: str
    device_type_hint: str
    source_url: str
    image_url: str
    alt_text: str = ""
    page_title: str = ""
    license: str = "unknown"
    usage_note: str = "research/internal only unless license verified"
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProcessedRecord:
    candidate_id: str
    query: str
    brand_hint: str
    device_type_hint: str
    source_url: str
    image_url: str
    alt_text: str = ""
    page_title: str = ""
    image_path: Optional[str] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    file_size: Optional[int] = None
    ocr_text: list[str] = field(default_factory=list)
    ocr_joined: str = ""
    brand: Optional[str] = None
    brand_source: Optional[str] = None
    has_visible_logo: bool = False
    phash: Optional[str] = None
    status: str = "candidate"
    reject_reason: Optional[str] = None
    license: str = "unknown"
    usage_note: str = "research/internal only unless license verified"
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
```

- [ ] **Step 2: Verify import**

Run: `cd apps/data-collector && python3 -c "from src.models import QueryRecord, Candidate, ProcessedRecord"`
Expected: no error.

- [ ] **Step 3: Commit**

```bash
git add apps/data-collector/src/models.py
git commit -m "feat(data-collector): add dataclass models"
```

---

## Task 3: Config

**Files:**
- Create: `apps/data-collector/src/config.py`
- Create: `apps/data-collector/.env.example`

- [ ] **Step 1: Write `config.py`**

```python
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COLLECTOR_", env_file=".env", extra="ignore")

    data_dir: Path = Path("data")
    search_engine: str = "bing"
    user_agent: str = "PanelLensResearchBot/0.1"
    request_timeout: int = 20
    max_concurrent_downloads: int = 8
    results_per_query: int = 12
    crawl_delay_seconds: float = 1.5

    min_image_width: int = 300
    min_image_height: int = 300
    min_image_file_size_kb: int = 20
    max_aspect_ratio: float = 6.0

    @property
    def collected_dir(self) -> Path:
        return self.data_dir / "collected"

    @property
    def seeds_dir(self) -> Path:
        return self.data_dir / "seeds"


def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 2: Write `.env.example`**

```env
COLLECTOR_DATA_DIR=data
COLLECTOR_SEARCH_ENGINE=bing
COLLECTOR_USER_AGENT=PanelLensResearchBot/0.1
COLLECTOR_REQUEST_TIMEOUT=20
COLLECTOR_MAX_CONCURRENT_DOWNLOADS=8
COLLECTOR_RESULTS_PER_QUERY=12
COLLECTOR_CRAWL_DELAY_SECONDS=1.5
COLLECTOR_MIN_IMAGE_WIDTH=300
COLLECTOR_MIN_IMAGE_HEIGHT=300
COLLECTOR_MIN_IMAGE_FILE_SIZE_KB=20
COLLECTOR_MAX_ASPECT_RATIO=6.0
```

- [ ] **Step 3: Verify**

Run: `cd apps/data-collector && python3 -c "from src.config import get_settings; s=get_settings(); print(s.search_engine, s.collected_dir)"`
Expected: prints `bing data/collected`.

- [ ] **Step 4: Commit**

```bash
git add apps/data-collector/src/config.py apps/data-collector/.env.example
git commit -m "feat(data-collector): add Settings config"
```

---

## Task 4: Seeds → query expansion (TDD)

**Files:**
- Create: `apps/data-collector/src/seeds.py`
- Test: `apps/data-collector/tests/test_seeds.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from src.seeds import generate_queries

BRANDS = ["LG", "Samsung"]
DEVICES = [
    {"device_type": "washing_machine", "queries": ["washing machine control panel"]},
    {"device_type": "tv_remote", "queries": ["TV remote control"]},
]


def test_generates_brand_device_query_product():
    queries = generate_queries(BRANDS, DEVICES)
    # 2 brands * 2 devices * 1 device-query each = 4 base queries
    assert len(queries) == 4
    texts = {q.query for q in queries}
    assert "LG washing machine control panel" in texts
    assert "Samsung TV remote control" in texts


def test_query_records_carry_brand_and_device():
    queries = generate_queries(BRANDS, DEVICES)
    lg_wm = next(q for q in queries if q.query == "LG washing machine control panel")
    assert lg_wm.brand == "LG"
    assert lg_wm.device_type == "washing_machine"
    assert lg_wm.intent == "panel_image"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=apps/data-collector pytest -q apps/data-collector/tests/test_seeds.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.seeds'`.

- [ ] **Step 3: Write `seeds.py`**

```python
from __future__ import annotations

import json
from pathlib import Path

from src.models import QueryRecord


def generate_queries(brands: list[str], device_entries: list[dict]) -> list[QueryRecord]:
    records: list[QueryRecord] = []
    for brand in brands:
        for entry in device_entries:
            device_type = entry["device_type"]
            for device_query in entry["queries"]:
                records.append(
                    QueryRecord(
                        query=f"{brand} {device_query}",
                        brand=brand,
                        device_type=device_type,
                    )
                )
    return records


def load_seeds(brands_path: Path, devices_path: Path) -> tuple[list[str], list[dict]]:
    brands = json.loads(brands_path.read_text())
    devices = json.loads(devices_path.read_text())
    return brands, devices
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=apps/data-collector pytest -q apps/data-collector/tests/test_seeds.py`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add apps/data-collector/src/seeds.py apps/data-collector/tests/test_seeds.py
git commit -m "feat(data-collector): query expansion from seeds"
```

---

## Task 5: Result-HTML extractor (TDD with fixture)

**Files:**
- Create: `apps/data-collector/tests/fixtures/bing_sample.html`
- Create: `apps/data-collector/src/crawl/extractors.py`
- Test: `apps/data-collector/tests/test_extractors.py`

Bing Images embeds each result as an `<a class="iusc" ...>` whose `m` attribute holds a
JSON blob with `murl` (image URL) and `purl` (source page URL), plus a `<img>` `alt`.

- [ ] **Step 1: Write the fixture `tests/fixtures/bing_sample.html`**

```html
<html><body>
<a class="iusc" m='{"murl":"https://img.example.com/lg-panel.jpg","purl":"https://shop.example.com/lg-washer","t":"LG Washer Panel"}'>
  <img alt="LG washing machine control panel" />
</a>
<a class="iusc" m='{"murl":"https://img.example.com/samsung-panel.png","purl":"https://shop.example.com/samsung-washer","t":"Samsung Panel"}'>
  <img alt="Samsung washing machine buttons" />
</a>
<a class="other">no m attr here</a>
</body></html>
```

- [ ] **Step 2: Write the failing test**

```python
from __future__ import annotations

from pathlib import Path

from src.crawl.extractors import extract_bing_candidates

FIXTURE = Path(__file__).parent / "fixtures" / "bing_sample.html"


def test_extracts_image_and_source_urls():
    html = FIXTURE.read_text()
    results = extract_bing_candidates(html)
    assert len(results) == 2
    first = results[0]
    assert first["image_url"] == "https://img.example.com/lg-panel.jpg"
    assert first["source_url"] == "https://shop.example.com/lg-washer"
    assert first["alt_text"] == "LG washing machine control panel"
    assert first["page_title"] == "LG Washer Panel"


def test_ignores_anchors_without_m_attribute():
    html = FIXTURE.read_text()
    results = extract_bing_candidates(html)
    assert all(r["image_url"].startswith("http") for r in results)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `PYTHONPATH=apps/data-collector pytest -q apps/data-collector/tests/test_extractors.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.crawl.extractors'`.

- [ ] **Step 4: Write `crawl/extractors.py`**

```python
from __future__ import annotations

import json
import re

# Matches the JSON blob carried in the `m` attribute of Bing Images result anchors.
_M_ATTR = re.compile(r"class=\"iusc\"[^>]*\bm='([^']+)'", re.IGNORECASE)
_ALT = re.compile(r"alt=\"([^\"]*)\"", re.IGNORECASE)


def extract_bing_candidates(html: str) -> list[dict]:
    """Parse a Bing Images result page into candidate dicts.

    Each dict has: image_url, source_url, alt_text, page_title.
    Anchors without a usable `m` blob are skipped.
    """
    results: list[dict] = []
    # Split per anchor so we can pair each `m` blob with the nearest alt text.
    for block in re.split(r"<a ", html):
        m = _M_ATTR.search("<a " + block)
        if not m:
            continue
        try:
            blob = json.loads(m.group(1).replace("&quot;", '"'))
        except json.JSONDecodeError:
            continue
        image_url = blob.get("murl", "")
        if not image_url.startswith("http"):
            continue
        alt = _ALT.search(block)
        results.append(
            {
                "image_url": image_url,
                "source_url": blob.get("purl", ""),
                "alt_text": alt.group(1) if alt else "",
                "page_title": blob.get("t", ""),
            }
        )
    return results
```

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH=apps/data-collector pytest -q apps/data-collector/tests/test_extractors.py`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add apps/data-collector/src/crawl/extractors.py apps/data-collector/tests/test_extractors.py apps/data-collector/tests/fixtures/bing_sample.html
git commit -m "feat(data-collector): Bing result extractor"
```

---

## Task 6: Playwright crawl driver (thin, manual-validated)

**Files:**
- Create: `apps/data-collector/src/crawl/image_search.py`

This stage is not unit-tested (live network + anti-bot are nondeterministic). Keep it
thin: it only drives the browser and delegates parsing to `extract_bing_candidates`.

- [ ] **Step 1: Write `crawl/image_search.py`**

```python
from __future__ import annotations

import time
from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright

from src.crawl.extractors import extract_bing_candidates


def _bing_url(query: str) -> str:
    return f"https://www.bing.com/images/search?q={quote_plus(query)}"


def fetch_candidates_html(query: str, user_agent: str, timeout_ms: int = 20000) -> str:
    """Open Bing Images for `query` with Playwright, scroll once, return page HTML."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=user_agent)
        try:
            page.goto(_bing_url(query), timeout=timeout_ms, wait_until="domcontentloaded")
            # Bing lazy-loads thumbnails; scroll to trigger a batch.
            for _ in range(3):
                page.mouse.wheel(0, 4000)
                page.wait_for_timeout(800)
            return page.content()
        finally:
            browser.close()


def search_query(query: str, user_agent: str, limit: int) -> list[dict]:
    """Return up to `limit` candidate dicts for a single query. Never raises."""
    try:
        html = fetch_candidates_html(query, user_agent)
    except Exception as exc:  # noqa: BLE001 - we log and continue on any crawl failure
        print(f"[crawl] FAILED query={query!r}: {exc}")
        return []
    candidates = extract_bing_candidates(html)
    return candidates[:limit]


def polite_sleep(seconds: float) -> None:
    time.sleep(seconds)
```

- [ ] **Step 2: Install the Playwright browser binary**

Run: `cd apps/data-collector && python3 -m playwright install chromium`
Expected: downloads Chromium (one-time).

- [ ] **Step 3: Smoke-check the driver compiles and imports**

Run: `cd apps/data-collector && python3 -c "from src.crawl.image_search import search_query, polite_sleep"`
Expected: no error.

- [ ] **Step 4: Commit**

```bash
git add apps/data-collector/src/crawl/image_search.py
git commit -m "feat(data-collector): Playwright Bing image-search driver"
```

---

## Task 7: Image downloader (TDD with mocked transport)

**Files:**
- Create: `apps/data-collector/src/download/downloader.py`
- Test: `apps/data-collector/tests/test_downloader.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=apps/data-collector pytest -q apps/data-collector/tests/test_downloader.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.download.downloader'`.

- [ ] **Step 3: Write `download/downloader.py`**

```python
from __future__ import annotations

from pathlib import Path

import httpx


def download_one(client: httpx.Client, url: str, dest: Path) -> dict:
    """Download a single URL to `dest`. Returns a result dict, never raises."""
    try:
        resp = client.get(url, follow_redirects=True)
    except httpx.HTTPError as exc:
        return {"ok": False, "url": url, "reason": f"error_{type(exc).__name__}"}
    if resp.status_code != 200:
        return {"ok": False, "url": url, "reason": f"http_{resp.status_code}"}
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    return {"ok": True, "url": url, "path": str(dest), "file_size": len(resp.content)}


def download_many(urls_dests: list[tuple[str, Path]], user_agent: str, timeout: int) -> list[dict]:
    """Download a list of (url, dest) pairs sequentially. Returns result dicts."""
    headers = {"User-Agent": user_agent}
    results: list[dict] = []
    with httpx.Client(headers=headers, timeout=timeout) as client:
        for url, dest in urls_dests:
            results.append(download_one(client, url, dest))
    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=apps/data-collector pytest -q apps/data-collector/tests/test_downloader.py`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add apps/data-collector/src/download/downloader.py apps/data-collector/tests/test_downloader.py
git commit -m "feat(data-collector): image downloader with result reporting"
```

---

## Task 8: Image validator (TDD with synthetic images)

**Files:**
- Create: `apps/data-collector/src/process/validator.py`
- Test: `apps/data-collector/tests/test_validator.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from PIL import Image

from src.process.validator import validate_image


def _make_image(tmp_path, name, w, h, color=(120, 120, 120)):
    path = tmp_path / name
    Image.new("RGB", (w, h), color).save(path)
    return path


def test_accepts_normal_image(tmp_path):
    path = _make_image(tmp_path, "ok.jpg", 800, 600)
    result = validate_image(path, min_w=300, min_h=300, min_kb=0, max_aspect=6.0)
    assert result["ok"] is True
    assert result["width"] == 800
    assert result["height"] == 600


def test_rejects_too_small(tmp_path):
    path = _make_image(tmp_path, "small.jpg", 100, 100)
    result = validate_image(path, min_w=300, min_h=300, min_kb=0, max_aspect=6.0)
    assert result["ok"] is False
    assert result["reason"] == "too_small"


def test_rejects_bad_aspect(tmp_path):
    path = _make_image(tmp_path, "wide.jpg", 4000, 400)
    result = validate_image(path, min_w=300, min_h=300, min_kb=0, max_aspect=6.0)
    assert result["ok"] is False
    assert result["reason"] == "bad_aspect"


def test_rejects_corrupt(tmp_path):
    path = tmp_path / "corrupt.jpg"
    path.write_bytes(b"not an image")
    result = validate_image(path, min_w=300, min_h=300, min_kb=0, max_aspect=6.0)
    assert result["ok"] is False
    assert result["reason"] == "decode_fail"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=apps/data-collector pytest -q apps/data-collector/tests/test_validator.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.process.validator'`.

- [ ] **Step 3: Write `process/validator.py`**

```python
from __future__ import annotations

from pathlib import Path

from PIL import Image


def validate_image(path: Path, min_w: int, min_h: int, min_kb: int, max_aspect: float) -> dict:
    """Validate a downloaded image. Returns {ok, reason, width, height}."""
    try:
        size_kb = path.stat().st_size / 1024
        with Image.open(path) as img:
            img.verify()
        with Image.open(path) as img:
            width, height = img.size
    except Exception:  # noqa: BLE001 - any decode/IO error means reject
        return {"ok": False, "reason": "decode_fail", "width": None, "height": None}

    if size_kb < min_kb:
        return {"ok": False, "reason": "too_small", "width": width, "height": height}
    if width < min_w or height < min_h:
        return {"ok": False, "reason": "too_small", "width": width, "height": height}
    long_side, short_side = max(width, height), min(width, height)
    if short_side == 0 or long_side / short_side > max_aspect:
        return {"ok": False, "reason": "bad_aspect", "width": width, "height": height}
    return {"ok": True, "reason": None, "width": width, "height": height}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=apps/data-collector pytest -q apps/data-collector/tests/test_validator.py`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add apps/data-collector/src/process/validator.py apps/data-collector/tests/test_validator.py
git commit -m "feat(data-collector): image validation rules"
```

---

## Task 9: Brand detection (TDD)

**Files:**
- Create: `apps/data-collector/src/process/brand.py`
- Test: `apps/data-collector/tests/test_brand.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from src.process.brand import detect_brand

def test_detects_lg_uppercase():
    brand, has_logo = detect_brand(["LG", "Cotton", "Spin"])
    assert brand == "LG"
    assert has_logo is True


def test_detects_samsung_titlecase():
    brand, has_logo = detect_brand(["samsung", "eco bubble"])
    assert brand == "Samsung"
    assert has_logo is True


def test_no_brand_found():
    brand, has_logo = detect_brand(["Start", "Pause", "Temp"])
    assert brand is None
    assert has_logo is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=apps/data-collector pytest -q apps/data-collector/tests/test_brand.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.process.brand'`.

- [ ] **Step 3: Write `process/brand.py`**

```python
from __future__ import annotations

from typing import Optional

KNOWN_BRANDS = [
    "lg", "samsung", "panasonic", "daikin", "sony", "toshiba",
    "electrolux", "sharp", "aqua", "midea", "hitachi",
    "mitsubishi", "whirlpool", "bosch", "philips",
]


def _canonical(brand: str) -> str:
    return "LG" if brand == "lg" else brand.title()


def detect_brand(ocr_text: list[str]) -> tuple[Optional[str], bool]:
    """Return (brand, has_visible_logo) from OCR text lines via substring match."""
    joined = " ".join(ocr_text).lower()
    for brand in KNOWN_BRANDS:
        if brand in joined:
            return _canonical(brand), True
    return None, False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=apps/data-collector pytest -q apps/data-collector/tests/test_brand.py`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add apps/data-collector/src/process/brand.py apps/data-collector/tests/test_brand.py
git commit -m "feat(data-collector): brand detection from OCR"
```

---

## Task 10: OCR wrapper (thin, manual-validated)

**Files:**
- Create: `apps/data-collector/src/process/ocr.py`

RapidOCR loads ONNX models lazily; wrap it so the rest of the code depends only on
`run_ocr(path) -> list[str]`.

- [ ] **Step 1: Write `process/ocr.py`**

```python
from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _engine():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def run_ocr(path: Path) -> list[str]:
    """Return OCR text lines for an image. Empty list if nothing/failure."""
    try:
        result, _ = _engine()(str(path))
    except Exception as exc:  # noqa: BLE001 - OCR must never crash the pipeline
        print(f"[ocr] FAILED path={path}: {exc}")
        return []
    if not result:
        return []
    # RapidOCR returns [[box, text, score], ...]
    return [line[1] for line in result if len(line) >= 2 and line[1]]
```

- [ ] **Step 2: Verify import**

Run: `cd apps/data-collector && python3 -c "from src.process.ocr import run_ocr"`
Expected: no error (engine not yet instantiated due to lazy load).

- [ ] **Step 3: Commit**

```bash
git add apps/data-collector/src/process/ocr.py
git commit -m "feat(data-collector): RapidOCR wrapper"
```

---

## Task 11: Gallery renderer (TDD)

**Files:**
- Create: `apps/data-collector/src/report/gallery.py`
- Test: `apps/data-collector/tests/test_gallery.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from src.report.gallery import render_gallery


def test_render_includes_record_fields():
    records = [
        {
            "candidate_id": "cand_000001",
            "query": "LG washing machine control panel",
            "image_path": "data/collected/raw/images/cand_000001.jpg",
            "brand": "LG",
            "device_type_hint": "washing_machine",
            "ocr_joined": "LG Cotton Spin",
            "source_url": "https://shop.example.com/lg",
            "status": "ocr_done",
            "reject_reason": None,
        }
    ]
    html = render_gallery(records)
    assert "cand_000001" in html
    assert "LG washing machine control panel" in html
    assert "LG Cotton Spin" in html
    assert "https://shop.example.com/lg" in html
    assert "<img" in html


def test_render_shows_reject_reason():
    records = [
        {
            "candidate_id": "cand_000002",
            "query": "Samsung washer",
            "image_path": "x.jpg",
            "brand": None,
            "device_type_hint": "washing_machine",
            "ocr_joined": "",
            "source_url": "https://x",
            "status": "rejected",
            "reject_reason": "too_small",
        }
    ]
    html = render_gallery(records)
    assert "too_small" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=apps/data-collector pytest -q apps/data-collector/tests/test_gallery.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.report.gallery'`.

- [ ] **Step 3: Write `report/gallery.py`**

```python
from __future__ import annotations

from jinja2 import Template

_TEMPLATE = Template(
    """<!doctype html><html><head><meta charset="utf-8">
<title>PanelLens Slice 1 Gallery</title>
<style>
body{font-family:sans-serif;background:#111;color:#eee}
.grid{display:flex;flex-wrap:wrap;gap:12px}
.card{width:260px;border:1px solid #333;padding:8px;border-radius:8px}
.card img{width:100%;height:180px;object-fit:contain;background:#000}
.rej{color:#f66}.brand{color:#6f6}
small{color:#999;word-break:break-all}
</style></head><body>
<h1>PanelLens Slice 1 — {{ records|length }} records</h1>
<div class="grid">
{% for r in records %}
  <div class="card">
    <img src="{{ r.image_path }}" alt="{{ r.candidate_id }}">
    <div><b>{{ r.candidate_id }}</b></div>
    <div>{{ r.query }}</div>
    <div class="brand">brand: {{ r.brand or "—" }} | {{ r.device_type_hint }}</div>
    <div>ocr: {{ r.ocr_joined }}</div>
    <div>status: {{ r.status }}
      {% if r.reject_reason %}<span class="rej">[{{ r.reject_reason }}]</span>{% endif %}
    </div>
    <small><a href="{{ r.source_url }}">{{ r.source_url }}</a></small>
  </div>
{% endfor %}
</div></body></html>"""
)


def render_gallery(records: list[dict]) -> str:
    return _TEMPLATE.render(records=records)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=apps/data-collector pytest -q apps/data-collector/tests/test_gallery.py`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add apps/data-collector/src/report/gallery.py apps/data-collector/tests/test_gallery.py
git commit -m "feat(data-collector): HTML review gallery renderer"
```

---

## Task 12: Stage script 01 — generate queries

**Files:**
- Create: `apps/data-collector/scripts/01_generate_queries.py`

- [ ] **Step 1: Write `scripts/01_generate_queries.py`**

```python
from __future__ import annotations

import json

from src.config import get_settings
from src.seeds import generate_queries, load_seeds


def main() -> None:
    s = get_settings()
    brands, devices = load_seeds(s.seeds_dir / "brands.json", s.seeds_dir / "device_types.json")
    queries = generate_queries(brands, devices)
    s.collected_dir.mkdir(parents=True, exist_ok=True)
    out = s.collected_dir / "queries.jsonl"
    with out.open("w") as f:
        for q in queries:
            f.write(json.dumps(q.to_dict()) + "\n")
    print(f"[01] wrote {len(queries)} queries -> {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run: `cd apps/data-collector && PYTHONPATH=. COLLECTOR_DATA_DIR=../../data python3 scripts/01_generate_queries.py`
Expected: prints `[01] wrote 195 queries -> ../../data/collected/queries.jsonl` (15 brands × 13 device-queries [4+3+2+2+2] = 195). Confirm the file exists and count > 0.

- [ ] **Step 3: Commit**

```bash
git add apps/data-collector/scripts/01_generate_queries.py
git commit -m "feat(data-collector): script 01 generate queries"
```

---

## Task 13: Stage script 02 — crawl candidates

**Files:**
- Create: `apps/data-collector/scripts/02_crawl_candidates.py`

- [ ] **Step 1: Write `scripts/02_crawl_candidates.py`**

```python
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from src.config import get_settings
from src.crawl.image_search import polite_sleep, search_query
from src.models import Candidate


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1000, help="max candidates total")
    args = parser.parse_args()

    s = get_settings()
    queries_path = s.collected_dir / "queries.jsonl"
    queries = [json.loads(line) for line in queries_path.read_text().splitlines() if line.strip()]

    out = s.collected_dir / "candidates.jsonl"
    s.collected_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    with out.open("w") as f:
        for q in queries:
            if count >= args.limit:
                break
            hits = search_query(q["query"], s.user_agent, s.results_per_query)
            for hit in hits:
                if count >= args.limit:
                    break
                count += 1
                cand = Candidate(
                    candidate_id=f"cand_{count:06d}",
                    query=q["query"],
                    brand_hint=q["brand"],
                    device_type_hint=q["device_type"],
                    source_url=hit["source_url"],
                    image_url=hit["image_url"],
                    alt_text=hit["alt_text"],
                    page_title=hit["page_title"],
                    created_at=_now(),
                )
                f.write(json.dumps(cand.to_dict()) + "\n")
            print(f"[02] query={q['query']!r} hits={len(hits)} total={count}")
            polite_sleep(s.crawl_delay_seconds)
    print(f"[02] wrote {count} candidates -> {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-run with a small limit (live network)**

Run: `cd apps/data-collector && PYTHONPATH=. COLLECTOR_DATA_DIR=../../data python3 scripts/02_crawl_candidates.py --limit 30`
Expected: produces `candidates.jsonl` with up to 30 records. If 0 records across queries, Bing is blocking — note it; this is the discovery-risk surfaced in the spec.

- [ ] **Step 3: Commit**

```bash
git add apps/data-collector/scripts/02_crawl_candidates.py
git commit -m "feat(data-collector): script 02 crawl candidates"
```

---

## Task 14: Stage script 03 — download + validate

**Files:**
- Create: `apps/data-collector/scripts/03_download_images.py`

- [ ] **Step 1: Write `scripts/03_download_images.py`**

```python
from __future__ import annotations

import json
import shutil
from pathlib import Path

from src.config import get_settings
from src.download.downloader import download_many
from src.process.validator import validate_image


def main() -> None:
    s = get_settings()
    cand_path = s.collected_dir / "candidates.jsonl"
    candidates = [json.loads(l) for l in cand_path.read_text().splitlines() if l.strip()]

    raw_images = s.collected_dir / "raw" / "images"
    raw_images.mkdir(parents=True, exist_ok=True)

    urls_dests = [(c["image_url"], raw_images / f"{c['candidate_id']}.jpg") for c in candidates]
    results = download_many(urls_dests, s.user_agent, s.request_timeout)

    report = {"total": len(candidates), "downloaded": 0, "validated": 0, "rejected": {}}
    by_id = {c["candidate_id"]: c for c in candidates}
    out = s.collected_dir / "metadata_downloaded.jsonl"

    with out.open("w") as f:
        for cand, res in zip(candidates, results):
            rec = dict(cand)
            if not res["ok"]:
                rec["status"] = "rejected"
                rec["reject_reason"] = "download_fail"
                _reject_count(report, "download_fail")
                _move_reject(s, None, "download_fail")  # nothing to move; count only
                f.write(json.dumps(rec) + "\n")
                continue
            report["downloaded"] += 1
            dest = Path(res["path"])
            v = validate_image(
                dest, s.min_image_width, s.min_image_height,
                s.min_image_file_size_kb, s.max_aspect_ratio,
            )
            rec["image_path"] = str(dest)
            rec["file_size"] = res["file_size"]
            rec["image_width"] = v["width"]
            rec["image_height"] = v["height"]
            if not v["ok"]:
                rec["status"] = "rejected"
                rec["reject_reason"] = v["reason"]
                _reject_count(report, v["reason"])
                _move_reject(s, dest, v["reason"])
                rec["image_path"] = None
            else:
                rec["status"] = "validated"
                report["validated"] += 1
            f.write(json.dumps(rec) + "\n")

    (s.collected_dir / "download_report.json").write_text(json.dumps(report, indent=2))
    print(f"[03] {report}")


def _reject_count(report: dict, reason: str) -> None:
    report["rejected"][reason] = report["rejected"].get(reason, 0) + 1


def _move_reject(s, dest, reason: str) -> None:
    if dest is None:
        return
    folder = s.collected_dir / "rejected" / reason
    folder.mkdir(parents=True, exist_ok=True)
    shutil.move(str(dest), str(folder / dest.name))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run: `cd apps/data-collector && PYTHONPATH=. COLLECTOR_DATA_DIR=../../data python3 scripts/03_download_images.py`
Expected: prints a report dict; `metadata_downloaded.jsonl`, `download_report.json`, `raw/images/`, and `rejected/<reason>/` populated.

- [ ] **Step 3: Commit**

```bash
git add apps/data-collector/scripts/03_download_images.py
git commit -m "feat(data-collector): script 03 download and validate"
```

---

## Task 15: Stage script 04 — OCR + brand + phash

**Files:**
- Create: `apps/data-collector/scripts/04_process_images.py`

- [ ] **Step 1: Write `scripts/04_process_images.py`**

```python
from __future__ import annotations

import json
import shutil
from pathlib import Path

import imagehash
from PIL import Image

from src.config import get_settings
from src.process.brand import detect_brand
from src.process.ocr import run_ocr


def main() -> None:
    s = get_settings()
    in_path = s.collected_dir / "metadata_downloaded.jsonl"
    records = [json.loads(l) for l in in_path.read_text().splitlines() if l.strip()]

    unverified = s.collected_dir / "unverified"
    unverified.mkdir(parents=True, exist_ok=True)
    out = s.collected_dir / "metadata_slice1.jsonl"

    with out.open("w") as f:
        for rec in records:
            if rec.get("status") != "validated" or not rec.get("image_path"):
                f.write(json.dumps(rec) + "\n")
                continue
            path = Path(rec["image_path"])
            ocr_lines = run_ocr(path)
            brand, has_logo = detect_brand(ocr_lines)
            rec["ocr_text"] = ocr_lines
            rec["ocr_joined"] = " ".join(ocr_lines)
            rec["brand"] = brand
            rec["brand_source"] = "ocr" if brand else None
            rec["has_visible_logo"] = has_logo
            try:
                with Image.open(path) as img:
                    rec["phash"] = str(imagehash.phash(img))
            except Exception:  # noqa: BLE001
                rec["phash"] = None
            rec["status"] = "ocr_done"
            if not has_logo:
                shutil.copy(str(path), str(unverified / path.name))
            f.write(json.dumps(rec) + "\n")

    print(f"[04] wrote {len(records)} records -> {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run: `cd apps/data-collector && PYTHONPATH=. COLLECTOR_DATA_DIR=../../data python3 scripts/04_process_images.py`
Expected: prints record count; `metadata_slice1.jsonl` has `ocr_text`, `has_visible_logo`, `phash` on validated rows; `unverified/` holds no-brand images.

- [ ] **Step 3: Commit**

```bash
git add apps/data-collector/scripts/04_process_images.py
git commit -m "feat(data-collector): script 04 OCR, brand detect, phash"
```

---

## Task 16: build_gallery script

**Files:**
- Create: `apps/data-collector/scripts/build_gallery.py`

- [ ] **Step 1: Write `scripts/build_gallery.py`**

```python
from __future__ import annotations

import json

from src.config import get_settings
from src.report.gallery import render_gallery


def main() -> None:
    s = get_settings()
    in_path = s.collected_dir / "metadata_slice1.jsonl"
    records = [json.loads(l) for l in in_path.read_text().splitlines() if l.strip()]
    # Make image paths relative to the gallery file location (collected_dir).
    for r in records:
        if r.get("image_path"):
            r["image_path"] = r["image_path"].split("collected/")[-1]
    html = render_gallery(records)
    out = s.collected_dir / "gallery.html"
    out.write_text(html)
    print(f"[gallery] wrote {len(records)} records -> {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run: `cd apps/data-collector && PYTHONPATH=. COLLECTOR_DATA_DIR=../../data python3 scripts/build_gallery.py`
Expected: prints record count; `data/collected/gallery.html` exists. Open in browser to review.

- [ ] **Step 3: Commit**

```bash
git add apps/data-collector/scripts/build_gallery.py
git commit -m "feat(data-collector): build_gallery script"
```

---

## Task 17: README + full test run

**Files:**
- Create: `apps/data-collector/README.md`

- [ ] **Step 1: Write `README.md`**

````markdown
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
````

- [ ] **Step 2: Run the full test suite**

Run: `cd apps/data-collector && PYTHONPATH=. pytest -q tests`
Expected: all tests pass (seeds, extractors, downloader, validator, brand, gallery).

- [ ] **Step 3: Commit**

```bash
git add apps/data-collector/README.md
git commit -m "docs(data-collector): README and run instructions"
```

---

## Task 18: Update .gitignore for collected data

**Files:**
- Modify: `.gitignore` (repo root)

Collected images/HTML are large and unreviewed — keep them out of git.

- [ ] **Step 1: Append to root `.gitignore`**

```gitignore
# data-collector Slice 1 runtime output (large, unreviewed)
data/collected/
```

- [ ] **Step 2: Verify nothing under data/collected is staged**

Run: `git status --porcelain data/collected`
Expected: no output (ignored).

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: ignore data-collector runtime output"
```

---

## Acceptance verification (run after all tasks)

1. `wc -l data/collected/candidates.jsonl` → ≥ 500 (run script 02 with `--limit 1000`;
   if Bing blocks, this is the discovery risk — fix before proceeding).
2. `cat data/collected/download_report.json` → `validated` ≥ 60% of `total`.
3. Every `status == "ocr_done"` row in `metadata_slice1.jsonl` has non-null
   `has_visible_logo` and an `ocr_text` list.
4. `ls data/collected/unverified/` → contains the no-brand images (not deleted).
5. Open `data/collected/gallery.html` → renders images, query, brand, OCR, source_url,
   reject reasons.
6. `PYTHONPATH=apps/data-collector pytest -q apps/data-collector/tests` → all green.
```
