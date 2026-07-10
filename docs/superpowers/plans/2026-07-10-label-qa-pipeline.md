# Label QA/QC Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn an appliance manual PDF and a control-panel photo into a draft label JSON — one bounding box and one Vietnamese function description per button — with a QC flag on every button a human must re-check.

**Architecture:** Four pure file-to-file stages (`extract`, `detect`, `describe`, `qc`) composed by `pipeline.py`. Only `gemini_client.py` touches the network, and it caches every call by content hash. `detect` never sees the manual; `describe` never sees the image; they meet only through `button_id`. Offline tool under `apps/vision-tools/scripts/`, never imported by the API.

**Tech Stack:** Python 3.12, `httpx` (already installed), `pypdf` (new), `Pillow` (already installed), `pytest`. Gemini REST API `v1beta/models/{model}:generateContent`. No SDK.

**Source spec:** `docs/superpowers/specs/2026-07-09-label-qa-pipeline-design.md`

**Branch:** `dev/label-qa-pipeline` (already created, cut from `dev/tts` after the 001 merge).

## Global Constraints

- Python `>=3.11` (`apps/vision-tools/pyproject.toml`). Work inside the `silvertech` conda env.
- Ruff `line-length = 100`.
- Tests never call the network. Every Gemini call in a test goes through an injected fake transport.
- Run tests with `PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/<file>` — this repo runs packages by path, not by install.
- Gemini `box_2d` is `[ymin, xmin, ymax, xmax]`, normalized to 0–1000. **y comes first.**
- Model id is `gemini-3.5-flash`, overridable with `GEMINI_MODEL`. API key from `GEMINI_API_KEY`.
- Nothing in this pipeline writes to `apps/api/silvertech.sqlite3`, and nothing overwrites a reviewed `*.json` label file. Output is `*.draft.json`.
- `qc.py` flags, never deletes. Every detection reaches the draft.
- Rounding convention: **round each corner, then subtract.** Never round the difference.

## Deviations from the spec (deliberate, with reasons)

Three. Each was forced by something the spec did not know.

1. **`gemini-3-flash` → `gemini-3.5-flash`.** The id in the spec's `detect.py` artifact does not exist. Google's image-understanding docs currently use `gemini-3.5-flash` in every example. Made configurable so the next rename costs an env var, not a code change.

2. **Eight modules, not seven: `geometry.py` is added.** The spec puts `to_bbox` in `detect.py` and never says where IoU lives, but `qc.py` (`bbox_overlap`) and `eval_detect.py` (matching) both need IoU. Importing `qc` from `eval_detect`, or `detect` from `qc`, would break the stage-isolation rule the spec's architecture rests on. `geometry.py` is a leaf: pure math, no I/O, no network, imported by three modules and importing none.

3. **Half-up rounding, not `round()`.** Python's `round()` is banker's rounding: `round(0.5) == 0` but `round(1.5) == 2`. A box edge landing exactly on `.5` would round in a direction that depends on its parity — reproducible, but for a reason no reader would guess. `_round_half_up` is explicit. It gives identical results on both spec examples; it only differs on exact halves.

One smaller thing, not worth a section: the spec says an unparseable model reply is "written to the artifact and the stage raises". No artifact exists at that point — the stage failed before writing one. The raw text is carried in the `GeminiError` message instead (first 500 characters), which serves the same purpose: you can see what the model actually said.

## Corrections to the spec's evaluation section

Read before Task 8. The spec's gold-set numbers were written from memory and two are wrong. Verified against the files on disk:

| Spec says | Actually |
|---|---|
| Panasonic has 15 labeled buttons | **16** — `micro_power` was backfilled in commit `2ef1ae5` |
| 26 buttons total | **27** |
| Electrolux image is `.png` | **`.jpg`** — `data/templates/electrolux_washer_ewf9024adsa.jpg` |

And one thing the spec did not notice, which changes what Task 8 can measure:

**Electrolux `button_id`s are `"1"` … `"11"`.** They are position numbers copied off a manual diagram, not slugs of any on-panel text. No slug of any `label_text` will ever equal `"7"`. So `button_id` accuracy is measurable **only against Panasonic's 16 buttons**; including Electrolux would drag the metric toward zero for a reason that has nothing to do with the model. Task 8 computes id accuracy over gold buttons whose id is not a bare integer, and prints the excluded count so the number is never read as if it covered all 27.

Box metrics (precision, recall, mean IoU) are unaffected — Electrolux boxes are real. Use all 27 there.

The spec's **recorded prediction** stands and should be checked on the first real run: the model will miss the icon-only `up`/`down` arrows, and `button_id` accuracy will land below recall. If it doesn't, an assumption in the spec is wrong.

## File Structure

```
apps/vision-tools/scripts/label_pipeline/
  __init__.py        # empty, marks the package
  geometry.py        # to_bbox, iou, bbox_area, center — pure math, imports nothing
  gemini_client.py   # the only module that touches the network; cache + retry + JSON parse
  extract.py         # manual.pdf          -> manual_text.json
  detect.py          # panel image         -> detections.json
  describe.py        # manual_text + ids   -> described.json
  qc.py              # rule checks -> per-button and per-template flags
  pipeline.py        # composes the four stages; CLI
  eval_detect.py     # detections vs gold labels: precision/recall/IoU/id accuracy

apps/vision-tools/tests/
  test_label_geometry.py
  test_label_gemini_client.py
  test_label_extract.py
  test_label_detect.py
  test_label_describe.py
  test_label_qc.py
  test_label_pipeline.py
  test_label_eval_detect.py
```

Tests sit flat in `tests/`, matching the existing `test_logo_anchor.py` layout and the `pythonpath = ["."]` in `pyproject.toml`.

Dependency edges, all pointing down, no cycles:

```
pipeline.py ──► extract.py ──► gemini_client.py
            ├─► detect.py   ──► gemini_client.py, geometry.py
            ├─► describe.py ──► gemini_client.py
            └─► qc.py       ──► geometry.py

eval_detect.py ──► geometry.py
```

`eval_detect.py` is not a stage. It reads two files and prints. It never runs inside `pipeline.py`.

---

## Task 1: Package scaffold and `geometry.py`

The coordinate conversion is the pipeline's most likely silent failure, so it is the first thing written and the first thing tested.

**Files:**
- Create: `apps/vision-tools/scripts/label_pipeline/__init__.py`
- Create: `apps/vision-tools/scripts/label_pipeline/geometry.py`
- Create: `apps/vision-tools/tests/test_label_geometry.py`
- Modify: `apps/vision-tools/pyproject.toml`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `to_bbox(box_2d: Sequence[int], *, width: int, height: int) -> dict[str, int]` — returns `{"x", "y", "width", "height"}`, absolute pixels.
  - `iou(a: dict, b: dict) -> float` — both boxes in `{"x","y","width","height"}` form.
  - `bbox_area(box: dict) -> int`
  - `center(box: dict) -> tuple[float, float]`

- [ ] **Step 1: Write the failing tests**

Create `apps/vision-tools/tests/test_label_geometry.py`:

```python
from __future__ import annotations

import pytest

from scripts.label_pipeline.geometry import bbox_area, center, iou, to_bbox

# Both gold images, deliberately non-square: a transposed axis cannot survive both.
PANASONIC = {"width": 5712, "height": 4284}
ELECTROLUX = {"width": 2560, "height": 810}


def test_box_2d_maps_y_first_not_x_first():
    # box_2d is [ymin, xmin, ymax, xmax] normalized to 0..1000.
    box = to_bbox([100, 500, 200, 750], **PANASONIC)
    assert box["x"] == 2856
    assert box["y"] == 428
    assert box["width"] == 1428
    assert box["height"] == 429


def test_box_2d_on_a_wide_image_exposes_a_transposed_axis():
    # 3.2:1. Reading box_2d as [xmin, ymin, ...] would put x at 256, not 1280.
    box = to_bbox([100, 500, 200, 750], **ELECTROLUX)
    assert box == {"x": 1280, "y": 81, "width": 640, "height": 81}


def test_corners_are_rounded_before_they_are_subtracted():
    # ymin 100 -> 428.4 -> 428;  ymax 200 -> 856.8 -> 857;  height = 857 - 428 = 429.
    # Rounding the difference instead gives round(428.4) = 428. The edge moves a pixel.
    box = to_bbox([100, 0, 200, 1000], **PANASONIC)
    assert box["height"] == 429


def test_exact_halves_round_up_not_to_even():
    # 500/1000 * 1 == 0.5 exactly. Python's round() is banker's rounding and would
    # return 0 here; _round_half_up returns 1. Only an exact half tells them apart,
    # so the assertion has to land on one.
    box = to_bbox([0, 0, 1000, 500], width=1, height=1)
    assert box["width"] == 1
    assert box["height"] == 1


def test_a_full_frame_box_spans_the_whole_image():
    box = to_bbox([0, 0, 1000, 1000], **ELECTROLUX)
    assert box == {"x": 0, "y": 0, "width": 2560, "height": 810}


def test_to_bbox_rejects_a_box_that_is_not_four_numbers():
    with pytest.raises(ValueError, match="four"):
        to_bbox([1, 2, 3], width=100, height=100)


def test_identical_boxes_have_iou_one():
    box = {"x": 10, "y": 10, "width": 20, "height": 20}
    assert iou(box, box) == pytest.approx(1.0)


def test_disjoint_boxes_have_iou_zero():
    a = {"x": 0, "y": 0, "width": 10, "height": 10}
    b = {"x": 100, "y": 100, "width": 10, "height": 10}
    assert iou(a, b) == 0.0


def test_boxes_that_only_touch_at_an_edge_have_iou_zero():
    a = {"x": 0, "y": 0, "width": 10, "height": 10}
    b = {"x": 10, "y": 0, "width": 10, "height": 10}
    assert iou(a, b) == 0.0


def test_half_overlap_has_iou_one_third():
    # intersection 50, union 150.
    a = {"x": 0, "y": 0, "width": 10, "height": 10}
    b = {"x": 5, "y": 0, "width": 10, "height": 10}
    assert iou(a, b) == pytest.approx(1 / 3)


def test_a_degenerate_box_has_iou_zero_and_never_divides_by_zero():
    a = {"x": 0, "y": 0, "width": 0, "height": 10}
    b = {"x": 0, "y": 0, "width": 10, "height": 10}
    assert iou(a, b) == 0.0


def test_bbox_area_and_center():
    box = {"x": 10, "y": 20, "width": 30, "height": 40}
    assert bbox_area(box) == 1200
    assert center(box) == (25.0, 40.0)
```

- [ ] **Step 2: Run the tests and watch them fail**

```bash
PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_label_geometry.py
```

Expected: collection error — `ModuleNotFoundError: No module named 'scripts.label_pipeline'`.

- [ ] **Step 3: Write `geometry.py`**

Create `apps/vision-tools/scripts/label_pipeline/__init__.py` as an empty file.

Create `apps/vision-tools/scripts/label_pipeline/geometry.py`:

```python
"""Pure geometry for the label pipeline. No I/O, no network, imports nothing local."""

from __future__ import annotations

import math
from collections.abc import Sequence

Bbox = dict[str, int]


def _round_half_up(value: float) -> int:
    # round() is banker's rounding: round(0.5) == 0 but round(1.5) == 2. A box edge
    # landing on an exact half would then move by a pixel depending on its parity.
    return int(math.floor(value + 0.5))


def to_bbox(box_2d: Sequence[int], *, width: int, height: int) -> Bbox:
    """Convert Gemini's [ymin, xmin, ymax, xmax] (0..1000) to absolute {x, y, width, height}.

    Two things happen here at once: the axis order is transposed, and the values are
    scaled by the image dimensions. Getting the order wrong yields boxes that look
    plausible in JSON and are wrong on the image.
    """
    if len(box_2d) != 4:
        raise ValueError(f"box_2d must be four numbers [ymin, xmin, ymax, xmax], got {box_2d!r}")
    ymin, xmin, ymax, xmax = box_2d
    x = _round_half_up(xmin / 1000 * width)
    y = _round_half_up(ymin / 1000 * height)
    return {
        "x": x,
        "y": y,
        "width": _round_half_up(xmax / 1000 * width) - x,
        "height": _round_half_up(ymax / 1000 * height) - y,
    }


def bbox_area(box: Bbox) -> int:
    return max(0, box["width"]) * max(0, box["height"])


def center(box: Bbox) -> tuple[float, float]:
    return (box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)


def iou(a: Bbox, b: Bbox) -> float:
    """Intersection over union. A degenerate box scores 0 rather than dividing by zero."""
    ax2, ay2 = a["x"] + a["width"], a["y"] + a["height"]
    bx2, by2 = b["x"] + b["width"], b["y"] + b["height"]
    overlap_w = min(ax2, bx2) - max(a["x"], b["x"])
    overlap_h = min(ay2, by2) - max(a["y"], b["y"])
    if overlap_w <= 0 or overlap_h <= 0:
        return 0.0
    intersection = overlap_w * overlap_h
    union = bbox_area(a) + bbox_area(b) - intersection
    if union <= 0:
        return 0.0
    return intersection / union
```

- [ ] **Step 4: Run the tests and watch them pass**

```bash
PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_label_geometry.py
```

Expected: `12 passed`.

- [ ] **Step 5: Declare the new dependencies**

In `apps/vision-tools/pyproject.toml`, add a `label` extra under `[project.optional-dependencies]`, leaving `opencv` and `dev` untouched:

```toml
[project.optional-dependencies]
opencv = ["opencv-python>=4.9"]
dev = ["pytest>=8.0"]
label = ["httpx>=0.27", "pypdf>=5.1", "pillow>=10.0"]
```

Install `pypdf` (`httpx` and `pillow` are already in the env):

```bash
conda activate silvertech
python -m pip install "pypdf>=5.1"
```

- [ ] **Step 6: Ignore the cache and the drafts**

Append to `.gitignore`, under the existing `# Local data and secrets` block:

```gitignore
.cache/
.pipeline/
data/manuals/*.pdf
data/templates/labels/*.draft.json
data/templates/labels/*.qc_report.json
```

Drafts are ignored on purpose: a draft is a proposal, and only the reviewed file a human renames belongs in git.

- [ ] **Step 7: Lint and commit**

```bash
ruff check apps/vision-tools/scripts/label_pipeline apps/vision-tools/tests/test_label_geometry.py
git add apps/vision-tools/scripts/label_pipeline .gitignore \
        apps/vision-tools/pyproject.toml apps/vision-tools/tests/test_label_geometry.py
git commit -m "feat(label-pipeline): convert Gemini box_2d to template pixels

box_2d is [ymin, xmin, ymax, xmax] normalized to 0-1000, while the label
schema is {x, y, width, height} in absolute pixels. Transposing the axes
silently produces plausible-looking, wrong boxes, so the conversion is
tested on both gold images, whose aspect ratios differ."
```

---

## Task 2: `gemini_client.py`

Everything that can fail on the network lives here, so no stage has to think about it.

**Files:**
- Create: `apps/vision-tools/scripts/label_pipeline/gemini_client.py`
- Create: `apps/vision-tools/tests/test_label_gemini_client.py`

**Interfaces:**
- Consumes: nothing local.
- Produces:
  - `class GeminiError(RuntimeError)`
  - `class GeminiClient` with:
    - `__init__(self, *, api_key: str, model: str = DEFAULT_MODEL, cache_dir: Path = DEFAULT_CACHE_DIR, transport: Transport | None = None, max_retries: int = 5, sleep: Callable[[float], None] = time.sleep)`
    - `generate_json(self, prompt: str, *, image: bytes | None = None, mime_type: str = "image/png", cache_salt: bytes = b"") -> dict`
    - `prompt_version(self, prompt: str) -> str` — returns `"sha256:<12 hex chars>"`
  - `Transport = Callable[[str, dict], tuple[int, dict]]` — `(url, payload) -> (status_code, body)`
  - `DEFAULT_MODEL = "gemini-3.5-flash"`
  - `load_api_key() -> str` — reads `GEMINI_API_KEY` from the environment, falling back to the repo `.env`.

- [ ] **Step 1: Write the failing tests**

Create `apps/vision-tools/tests/test_label_gemini_client.py`:

```python
from __future__ import annotations

import json

import pytest

from scripts.label_pipeline.gemini_client import GeminiClient, GeminiError


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


def test_a_500_is_retried(tmp_path):
    client, transport = make_client(tmp_path, [(503, {}), (200, ok_body({"a": 1}))])
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
```

- [ ] **Step 2: Run the tests and watch them fail**

```bash
PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_label_gemini_client.py
```

Expected: `ModuleNotFoundError: No module named 'scripts.label_pipeline.gemini_client'`.

- [ ] **Step 3: Write `gemini_client.py`**

Create `apps/vision-tools/scripts/label_pipeline/gemini_client.py`:

```python
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

# label_pipeline/ sits one level deeper than the sibling scripts, so this is
# parents[4], not the parents[3] those files use.
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
        # None and b"" produce different payloads, so they must not share a key.
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
```

- [ ] **Step 4: Run the tests and watch them pass**

```bash
PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_label_gemini_client.py
```

Expected: `16 passed`. (`base64.b64encode(b"\x89PNG-bytes")` is `iVBORy1ieXRlcw==` — verified, not guessed.)

- [ ] **Step 5: Lint and commit**

```bash
ruff check apps/vision-tools/scripts/label_pipeline apps/vision-tools/tests/test_label_gemini_client.py
git add apps/vision-tools/scripts/label_pipeline/gemini_client.py \
        apps/vision-tools/tests/test_label_gemini_client.py
git commit -m "feat(label-pipeline): add caching, retrying Gemini client

Cache key is the model plus a hash of the prompt plus a hash of the image,
so an edited prompt cannot read an entry written by the old one. The api key
is excluded: it is a credential, not an input.

429 and 5xx back off and retry; 4xx and unparseable JSON raise at once,
because neither becomes true on a second attempt."
```

---

## Task 3: `extract.py` — manual PDF to text

**Files:**
- Create: `apps/vision-tools/scripts/label_pipeline/extract.py`
- Create: `apps/vision-tools/tests/test_label_extract.py`

**Interfaces:**
- Consumes: `GeminiClient.generate_json` (Task 2).
- Produces:
  - `extract_manual(pages: list[PageSource], *, client: GeminiClient, min_chars: int = 40) -> list[dict]` — the pure core, one dict per page with keys `page`, `mode`, `text`, and `error` on failure.
  - `class PageSource(NamedTuple)`: `number: int`, `text: str`, `image: bytes | None`
  - `read_pdf(path: Path) -> list[PageSource]` — the only part that touches `pypdf`.
  - `write_manual_text(pdf_path: Path, out_path: Path, *, client: GeminiClient, min_chars: int = 40) -> dict`
  - `OCR_PROMPT: str`

Splitting `read_pdf` from `extract_manual` is what lets the tests drive the threshold branch with plain tuples instead of building PDFs.

- [ ] **Step 1: Write the failing tests**

Create `apps/vision-tools/tests/test_label_extract.py`:

```python
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
```

- [ ] **Step 2: Run the tests and watch them fail**

```bash
PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_label_extract.py
```

Expected: `ModuleNotFoundError: No module named 'scripts.label_pipeline.extract'`.

- [ ] **Step 3: Write `extract.py`**

Create `apps/vision-tools/scripts/label_pipeline/extract.py`:

```python
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
```

- [ ] **Step 4: Run the tests and watch them pass**

```bash
PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_label_extract.py
```

Expected: `8 passed`.

- [ ] **Step 5: Commit**

```bash
ruff check apps/vision-tools/scripts/label_pipeline apps/vision-tools/tests/test_label_extract.py
git add apps/vision-tools/scripts/label_pipeline/extract.py \
        apps/vision-tools/tests/test_label_extract.py
git commit -m "feat(label-pipeline): read manual pages, OCR the scanned ones

A page whose text layer is shorter than 40 characters is treated as a scan.
Both modes occur inside one manual, so mode is recorded per page: the first
question about a wrong description is whether that page was read or OCR'd.

A page that fails fails alone. Losing page 11 to a rate limit must not
discard the ten pages already transcribed."
```

---

## Task 4: `detect.py` — panel image to boxes

**Files:**
- Create: `apps/vision-tools/scripts/label_pipeline/detect.py`
- Create: `apps/vision-tools/tests/test_label_detect.py`

**Interfaces:**
- Consumes: `to_bbox` (Task 1), `GeminiClient` (Task 2).
- Produces:
  - `slug(value: str) -> str` — the Python twin of `label_web/app.js`'s `slug()`.
  - `detect_buttons(reply: dict, *, width: int, height: int) -> dict` — pure; converts a model reply into the `detections.json` body.
  - `write_detections(image_path: Path, out_path: Path, *, client: GeminiClient) -> dict`
  - `DETECT_PROMPT: str`

`detect.py` does not know the manual exists. That is the boundary.

- [ ] **Step 1: Write the failing tests**

Create `apps/vision-tools/tests/test_label_detect.py`:

```python
from __future__ import annotations

import pytest

from scripts.label_pipeline.detect import detect_buttons, slug

PANASONIC = {"width": 5712, "height": 4284}


def reply(*items, regions=None):
    body = {"detections": list(items)}
    if regions:
        body["regions"] = regions
    return body


def test_slug_matches_the_label_web_rules():
    # label_web/app.js: trim, lowercase, strip diacritics, non-alphanumerics to _,
    # then trim leading and trailing underscores.
    assert slug("  Micro Power ") == "micro_power"
    assert slug("Time 10 min") == "time_10_min"
    assert slug("Stop/Reset") == "stop_reset"
    assert slug("Vi sóng") == "vi_song"
    assert slug("Quick 30!!") == "quick_30"
    assert slug("---") == ""
    assert slug("") == ""


def test_a_detection_becomes_a_button_with_a_slugged_id():
    body = detect_buttons(
        reply({"label_text": "Micro Power", "box_2d": [100, 500, 200, 750], "confidence": 0.86}),
        **PANASONIC,
    )
    button = body["detections"][0]
    assert button["button_id"] == "micro_power"
    assert button["label_text"] == "Micro Power"
    assert button["confidence"] == 0.86
    assert button["bbox_template_coordinates"] == {
        "x": 2856, "y": 428, "width": 1428, "height": 429
    }


def test_the_raw_box_2d_is_kept_beside_the_converted_box():
    # When a box is wrong, this distinguishes "the model guessed wrong" from "our
    # conversion is wrong", without spending another API call.
    body = detect_buttons(
        reply({"label_text": "Start", "box_2d": [1, 2, 3, 4], "confidence": 0.9}), **PANASONIC
    )
    assert body["detections"][0]["box_2d"] == [1, 2, 3, 4]


def test_an_icon_only_button_gets_a_null_id_and_is_never_invented():
    # A wrong button_id breaks the validation gate in services/guidance_service.py.
    body = detect_buttons(
        reply({"label_text": "", "box_2d": [1, 2, 3, 4], "confidence": 0.4}), **PANASONIC
    )
    assert body["detections"][0]["button_id"] is None


def test_a_detection_without_a_box_is_dropped_with_a_recorded_reason():
    body = detect_buttons(
        reply(
            {"label_text": "Start", "confidence": 0.9},
            {"label_text": "Stop", "box_2d": [1, 2, 3, 4], "confidence": 0.9},
        ),
        **PANASONIC,
    )
    assert [d["label_text"] for d in body["detections"]] == ["Stop"]
    assert body["dropped"] == [{"label_text": "Start", "reason": "no box_2d"}]


def test_a_malformed_box_is_dropped_rather_than_crashing_the_stage():
    body = detect_buttons(reply({"label_text": "Start", "box_2d": [1, 2, 3]}), **PANASONIC)
    assert body["detections"] == []
    assert body["dropped"][0]["reason"].startswith("bad box_2d")


def test_a_missing_confidence_defaults_to_zero_not_to_one():
    # Absent evidence is not evidence of correctness; low_confidence should flag it.
    body = detect_buttons(reply({"label_text": "Start", "box_2d": [1, 2, 3, 4]}), **PANASONIC)
    assert body["detections"][0]["confidence"] == 0.0


def test_logo_and_panel_regions_are_converted_too():
    body = detect_buttons(
        reply(regions={"logo": [100, 500, 200, 750], "panel": [0, 0, 1000, 1000]}), **PANASONIC
    )
    assert body["regions"]["logo"] == {"x": 2856, "y": 428, "width": 1428, "height": 429}
    assert body["regions"]["panel"] == {"x": 0, "y": 0, "width": 5712, "height": 4284}


def test_a_missing_region_is_null_not_absent():
    body = detect_buttons(reply(), **PANASONIC)
    assert body["regions"] == {"logo": None, "panel": None}


def test_the_image_dimensions_are_recorded():
    body = detect_buttons(reply(), **PANASONIC)
    assert body["image"]["width"] == 5712
    assert body["image"]["height"] == 4284


def test_a_reply_with_no_detections_key_raises():
    with pytest.raises(ValueError, match="detections"):
        detect_buttons({"buttons": []}, **PANASONIC)
```

- [ ] **Step 2: Run the tests and watch them fail**

```bash
PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_label_detect.py
```

Expected: `ModuleNotFoundError: No module named 'scripts.label_pipeline.detect'`.

- [ ] **Step 3: Write `detect.py`**

Create `apps/vision-tools/scripts/label_pipeline/detect.py`:

```python
"""Stage 2: panel image -> detections.json.

This module does not know the manual exists. It sees pixels and returns boxes.
It meets describe.py only through button_id.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from scripts.label_pipeline.gemini_client import GeminiClient
from scripts.label_pipeline.geometry import to_bbox

DETECT_PROMPT = """You are looking at a photograph of a household appliance control panel.

Find every button, knob, dial, and touch key on the panel.

For each one return:
  - "label_text": the text printed on or immediately beside the control, copied exactly
    as it appears. If the control carries no text at all (an icon-only arrow, for
    example), return an empty string. Never invent a name.
  - "box_2d": [ymin, xmin, ymax, xmax], normalized to 0-1000.
  - "confidence": your confidence between 0 and 1.

Also return "regions":
  - "logo": box_2d around the manufacturer's brand logo.
  - "panel": box_2d around the whole control panel.

Return JSON:
{"detections": [{"label_text": "...", "box_2d": [0,0,0,0], "confidence": 0.0}],
 "regions": {"logo": [0,0,0,0], "panel": [0,0,0,0]}}
"""

MIME_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def slug(value: str) -> str:
    """Python twin of slug() in label_web/app.js. The two must agree or ids diverge."""
    text = unicodedata.normalize("NFD", str(value or "").strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _region(box_2d: object, width: int, height: int) -> dict[str, int] | None:
    if not isinstance(box_2d, list) or len(box_2d) != 4:
        return None
    return to_bbox(box_2d, width=width, height=height)


def detect_buttons(reply: dict, *, width: int, height: int) -> dict:
    if "detections" not in reply:
        raise ValueError(f"model reply has no 'detections' key: {sorted(reply)}")

    detections: list[dict] = []
    dropped: list[dict] = []
    for item in reply["detections"]:
        label_text = str(item.get("label_text") or "")
        box_2d = item.get("box_2d")
        if box_2d is None:
            dropped.append({"label_text": label_text, "reason": "no box_2d"})
            continue
        try:
            bbox = to_bbox(box_2d, width=width, height=height)
        except (ValueError, TypeError) as exc:
            dropped.append({"label_text": label_text, "reason": f"bad box_2d: {exc}"})
            continue
        button_id = slug(label_text) or None
        detections.append(
            {
                "button_id": button_id,
                "label_text": label_text,
                "box_2d": list(box_2d),
                "bbox_template_coordinates": bbox,
                # Absent confidence is not evidence of correctness.
                "confidence": float(item.get("confidence") or 0.0),
            }
        )

    regions = reply.get("regions") or {}
    return {
        "image": {"width": width, "height": height},
        "detections": detections,
        "dropped": dropped,
        "regions": {
            "logo": _region(regions.get("logo"), width, height),
            "panel": _region(regions.get("panel"), width, height),
        },
    }


def write_detections(image_path: Path, out_path: Path, *, client: GeminiClient) -> dict:
    from PIL import Image

    with Image.open(image_path) as image:
        width, height = image.size
    image_bytes = image_path.read_bytes()
    mime = MIME_TYPES.get(image_path.suffix.lower(), "image/png")

    # A failed detect fails the run: with no boxes there is nothing to emit.
    reply = client.generate_json(DETECT_PROMPT, image=image_bytes, mime_type=mime)
    body = detect_buttons(reply, width=width, height=height)
    body["image"]["path"] = str(image_path)
    body["model"] = client.model
    body["prompt_version"] = client.prompt_version(DETECT_PROMPT)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    return body
```

- [ ] **Step 4: Run the tests and watch them pass**

```bash
PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_label_detect.py
```

Expected: `11 passed`.

- [ ] **Step 5: Check the slug twin against the real thing**

The Python `slug` and the JavaScript `slug` must agree, or a re-labelled button silently changes id. Verify on the gold ids:

```bash
PYTHONPATH=apps/vision-tools python -c "
from scripts.label_pipeline.detect import slug
cases = {'Micro Power': 'micro_power', 'Time 10 min': 'time_10_min',
         'Stop/Reset': 'stop_reset', 'Turbo Defrost': 'turbo_defrost',
         'Auto Menu': 'auto_menu', 'Quick 30': 'quick_30', 'Add Time': 'add_time'}
bad = {k: slug(k) for k, v in cases.items() if slug(k) != v}
print('MISMATCH:', bad) if bad else print('slug agrees with label_web on all', len(cases))
"
```

Expected: `slug agrees with label_web on all 7`.

- [ ] **Step 6: Commit**

```bash
ruff check apps/vision-tools/scripts/label_pipeline apps/vision-tools/tests/test_label_detect.py
git add apps/vision-tools/scripts/label_pipeline/detect.py \
        apps/vision-tools/tests/test_label_detect.py
git commit -m "feat(label-pipeline): detect panel buttons, logo and panel regions

The model is never asked to invent a button_id. It returns the text printed
on the control; the id is slugged from that text with the same rules as
label_web/app.js. An icon-only control gets a null id and a QC flag, because
a wrong id would breach the button_id gate in guidance_service.py.

The raw box_2d is stored beside the converted box so that a wrong box can be
blamed on the model or on our conversion without another API call."
```

---

## Task 5: `describe.py` — manual text to Vietnamese descriptions

**Files:**
- Create: `apps/vision-tools/scripts/label_pipeline/describe.py`
- Create: `apps/vision-tools/tests/test_label_describe.py`

**Interfaces:**
- Consumes: `GeminiClient` (Task 2), `manual_full_text` (Task 3).
- Produces:
  - `describe_buttons(reply: dict, *, button_ids: list[str]) -> list[dict]` — pure; each dict has `button_id`, `vietnamese_name`, `function_description`, `manual_evidence`.
  - `write_descriptions(manual_text: dict, detections: dict, out_path: Path, *, client: GeminiClient) -> dict`
  - `DESCRIBE_PROMPT: str`

`describe.py` does not know the image exists. It receives ids and label texts, nothing else.

- [ ] **Step 1: Write the failing tests**

Create `apps/vision-tools/tests/test_label_describe.py`:

```python
from __future__ import annotations

import json

import pytest

from scripts.label_pipeline.describe import describe_buttons, write_descriptions


def test_a_described_button_carries_its_evidence():
    reply = {
        "buttons": [
            {
                "button_id": "micro_power",
                "vietnamese_name": "Vi sóng",
                "function_description": "chọn mức công suất vi sóng",
                "manual_evidence": {"page": 4, "quote": "Nhấn Micro Power để chọn công suất."},
            }
        ]
    }
    described = describe_buttons(reply, button_ids=["micro_power"])
    assert described[0]["vietnamese_name"] == "Vi sóng"
    assert described[0]["manual_evidence"]["page"] == 4


def test_a_button_the_model_skipped_still_appears_with_blank_fields():
    # qc.py flags it as missing_name. Dropping it here would hide a button.
    described = describe_buttons({"buttons": []}, button_ids=["start", "stop"])
    assert [b["button_id"] for b in described] == ["start", "stop"]
    assert described[0]["vietnamese_name"] == ""
    assert described[0]["function_description"] == ""
    assert described[0]["manual_evidence"] is None


def test_a_button_the_model_invented_is_discarded():
    # detect.py decides which buttons exist. describe.py may not add to that list.
    reply = {"buttons": [{"button_id": "ghost", "vietnamese_name": "Ma", "function_description": "x"}]}
    described = describe_buttons(reply, button_ids=["start"])
    assert [b["button_id"] for b in described] == ["start"]


def test_the_output_order_follows_the_detected_ids():
    reply = {"buttons": [
        {"button_id": "stop", "vietnamese_name": "Dừng", "function_description": "a"},
        {"button_id": "start", "vietnamese_name": "Bắt đầu", "function_description": "b"},
    ]}
    described = describe_buttons(reply, button_ids=["start", "stop"])
    assert [b["button_id"] for b in described] == ["start", "stop"]


def test_a_duplicate_id_in_the_reply_keeps_the_first():
    reply = {"buttons": [
        {"button_id": "start", "vietnamese_name": "Một", "function_description": "a"},
        {"button_id": "start", "vietnamese_name": "Hai", "function_description": "b"},
    ]}
    described = describe_buttons(reply, button_ids=["start"])
    assert len(described) == 1
    assert described[0]["vietnamese_name"] == "Một"


def test_a_reply_without_a_buttons_key_raises():
    with pytest.raises(ValueError, match="buttons"):
        describe_buttons({"items": []}, button_ids=["start"])


def test_write_descriptions_skips_null_ids_and_writes_the_file(tmp_path):
    manual_text = {"source": "m.pdf", "pages": [{"page": 1, "mode": "text_layer", "text": "Start."}]}
    detections = {"detections": [
        {"button_id": "start", "label_text": "Start"},
        {"button_id": None, "label_text": ""},
    ]}

    class FakeClient:
        model = "fake-model"
        captured_prompt = ""

        def prompt_version(self, prompt):
            return "sha256:fake"

        def generate_json(self, prompt, *, image=None, mime_type="image/png", cache_salt=b""):
            FakeClient.captured_prompt = prompt
            assert image is None  # describe.py must never see the image
            return {"buttons": [{"button_id": "start", "vietnamese_name": "Bắt đầu",
                                 "function_description": "bắt đầu nấu",
                                 "manual_evidence": {"page": 1, "quote": "Start."}}]}

    out = tmp_path / "described.json"
    body = write_descriptions(manual_text, detections, out, client=FakeClient())

    assert json.loads(out.read_text(encoding="utf-8")) == body
    assert [b["button_id"] for b in body["buttons"]] == ["start"]
    assert "Start." in FakeClient.captured_prompt  # the manual text reached the prompt
```

- [ ] **Step 2: Run the tests and watch them fail**

```bash
PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_label_describe.py
```

Expected: `ModuleNotFoundError: No module named 'scripts.label_pipeline.describe'`.

- [ ] **Step 3: Write `describe.py`**

Create `apps/vision-tools/scripts/label_pipeline/describe.py`:

```python
"""Stage 3: manual text + detected ids -> Vietnamese names and descriptions.

This module does not know the image exists. detect.py owns which buttons exist;
describe.py may only fill in words for the ids it is handed.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.label_pipeline.extract import manual_full_text
from scripts.label_pipeline.gemini_client import GeminiClient

DESCRIBE_PROMPT = """Bạn đang đọc sách hướng dẫn sử dụng của một thiết bị gia dụng.

Dưới đây là nội dung sách hướng dẫn, và danh sách các nút đã được phát hiện trên bảng
điều khiển. Với mỗi nút, hãy viết:

  - "vietnamese_name": tên ngắn gọn bằng tiếng Việt, dùng để đọc to cho người lớn tuổi.
    Không bao giờ chứa button_id thô (ví dụ "time_1_min").
  - "function_description": công dụng của nút, bằng tiếng Việt.
  - "manual_evidence": {"page": <số trang>, "quote": "<câu trích nguyên văn từ sách>"}
    Câu trích phải xuất hiện y nguyên trong nội dung sách bên dưới. Nếu sách không nói
    gì về nút này, đặt "manual_evidence": null và để mô tả trống.

Không bịa. Không thêm nút nào ngoài danh sách.

NỘI DUNG SÁCH:
{manual}

CÁC NÚT ĐÃ PHÁT HIỆN:
{buttons}

Trả về JSON:
{{"buttons": [{{"button_id": "...", "vietnamese_name": "...",
  "function_description": "...", "manual_evidence": {{"page": 1, "quote": "..."}}}}]}}
"""


def _blank(button_id: str) -> dict:
    return {
        "button_id": button_id,
        "vietnamese_name": "",
        "function_description": "",
        "manual_evidence": None,
    }


def describe_buttons(reply: dict, *, button_ids: list[str]) -> list[dict]:
    if "buttons" not in reply:
        raise ValueError(f"model reply has no 'buttons' key: {sorted(reply)}")

    by_id: dict[str, dict] = {}
    for item in reply["buttons"]:
        button_id = item.get("button_id")
        # detect.py decides which buttons exist; a first answer wins over a repeat.
        if button_id in button_ids and button_id not in by_id:
            by_id[button_id] = {
                "button_id": button_id,
                "vietnamese_name": str(item.get("vietnamese_name") or ""),
                "function_description": str(item.get("function_description") or ""),
                "manual_evidence": item.get("manual_evidence") or None,
            }
    # A button the model skipped still appears, blank, for qc.py to flag.
    return [by_id.get(button_id, _blank(button_id)) for button_id in button_ids]


def write_descriptions(
    manual_text: dict,
    detections: dict,
    out_path: Path,
    *,
    client: GeminiClient,
) -> dict:
    button_ids = [d["button_id"] for d in detections["detections"] if d.get("button_id")]
    listing = "\n".join(
        f"- {d['button_id']}: chữ in trên nút là \"{d['label_text']}\""
        for d in detections["detections"]
        if d.get("button_id")
    )
    manual = manual_full_text(manual_text)
    prompt = DESCRIBE_PROMPT.format(manual=manual, buttons=listing)

    # Both the manual and the id listing are interpolated into the prompt, and
    # GeminiClient keys its cache on a hash of the prompt. No extra salt is needed.
    reply = client.generate_json(prompt)

    body = {
        "model": client.model,
        "prompt_version": client.prompt_version(prompt),
        "buttons": describe_buttons(reply, button_ids=button_ids),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    return body
```

- [ ] **Step 4: Run the tests and watch them pass**

```bash
PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_label_describe.py
```

Expected: `7 passed`.

- [ ] **Step 5: Commit**

```bash
ruff check apps/vision-tools/scripts/label_pipeline apps/vision-tools/tests/test_label_describe.py
git add apps/vision-tools/scripts/label_pipeline/describe.py \
        apps/vision-tools/tests/test_label_describe.py
git commit -m "feat(label-pipeline): describe buttons from the manual

Every description carries a manual_evidence quote. That turns 'the model
invented a description' from a silent bug into one qc.py can check, by
looking the quote up in manual_text.json.

detect.py owns the button list. A button the model skipped comes back blank
for qc to flag; a button the model invented is discarded."
```

---

## Task 6: `qc.py` — the rules

**Files:**
- Create: `apps/vision-tools/scripts/label_pipeline/qc.py`
- Create: `apps/vision-tools/tests/test_label_qc.py`

**Interfaces:**
- Consumes: `iou`, `bbox_area`, `center` (Task 1).
- Produces:
  - `run_qc(buttons: list[dict], *, manual_text: str, image: dict, panel_bbox: dict | None, confidence_threshold: float = 0.5, iou_threshold: float = 0.3, min_area_ratio: float = 0.001) -> tuple[list[dict], dict]`
    - `buttons`: merged detection+description dicts, each with `button_id`, `vietnamese_name`, `function_description`, `manual_evidence`, `bbox_template_coordinates`, `confidence`.
    - returns `(buttons_with_qc, report)`. Each button gains `"qc": {"status", "issues", "confidence"}`.
    - `report` has `template_issues: list[dict]`, `counts: {"total", "pass", "flag"}`.
  - `manual_button_names(manual_text: str, buttons: list[dict]) -> ...` is *not* a public name — the manual cross-check lives inside `run_qc`.

Flags, never deletes. `len(buttons_with_qc) == len(buttons)`, always.

- [ ] **Step 1: Write the failing tests**

Create `apps/vision-tools/tests/test_label_qc.py`:

```python
from __future__ import annotations

from scripts.label_pipeline.qc import run_qc

IMAGE = {"width": 1000, "height": 1000}
PANEL = {"x": 0, "y": 0, "width": 1000, "height": 1000}
MANUAL = "Nhấn nút Start để bắt đầu. Nhấn Stop để dừng."


def button(**overrides) -> dict:
    base = {
        "button_id": "start",
        "label_text": "Start",
        "vietnamese_name": "Bắt đầu",
        "function_description": "bắt đầu nấu",
        "manual_evidence": {"page": 1, "quote": "Nhấn nút Start để bắt đầu."},
        "bbox_template_coordinates": {"x": 100, "y": 100, "width": 100, "height": 100},
        "confidence": 0.9,
    }
    return {**base, **overrides}


def issues_for(buttons, **kwargs) -> list[list[str]]:
    checked, _report = run_qc(
        buttons, manual_text=MANUAL, image=IMAGE, panel_bbox=PANEL, **kwargs
    )
    return [b["qc"]["issues"] for b in checked]


def test_a_clean_button_passes():
    checked, report = run_qc([button()], manual_text=MANUAL, image=IMAGE, panel_bbox=PANEL)
    assert checked[0]["qc"] == {"status": "pass", "issues": [], "confidence": 0.9}
    assert report["counts"] == {"total": 1, "pass": 1, "flag": 0}


def test_no_rule_ever_drops_a_button():
    broken = [button(button_id=None), button(button_id="x", vietnamese_name=""), button()]
    checked, _ = run_qc(broken, manual_text=MANUAL, image=IMAGE, panel_bbox=PANEL)
    assert len(checked) == 3


def test_missing_id_is_flagged():
    assert "missing_id" in issues_for([button(button_id=None)])[0]
    assert "missing_id" in issues_for([button(button_id="  ")])[0]


def test_missing_name_is_flagged():
    assert "missing_name" in issues_for([button(vietnamese_name="")])[0]
    assert "missing_name" in issues_for([button(vietnamese_name="   ")])[0]


def test_raw_id_in_text_is_flagged():
    # Mirrors the API bug where the LLM echoed time_1_min into spoken text and gTTS
    # read it aloud as "tam gach duoi mot gach duoi min".
    bad = button(button_id="time_1_min", function_description="Nhấn time_1_min một lần.")
    assert "raw_id_in_text" in issues_for([bad])[0]


def test_raw_id_in_the_vietnamese_name_is_also_flagged():
    bad = button(button_id="time_1_min", vietnamese_name="time_1_min")
    assert "raw_id_in_text" in issues_for([bad])[0]


def test_a_single_word_id_that_is_a_real_vietnamese_word_is_not_flagged():
    # "up" as a substring of "Cúp điện" must not trip the rule; match on word bounds.
    ok = button(button_id="up", vietnamese_name="Tăng", function_description="Tăng thời gian.")
    assert "raw_id_in_text" not in issues_for([ok])[0]


def test_no_evidence_is_flagged_when_the_quote_is_not_in_the_manual():
    invented = button(manual_evidence={"page": 9, "quote": "Câu này không có trong sách."})
    assert "no_evidence" in issues_for([invented])[0]


def test_no_evidence_is_flagged_when_evidence_is_null():
    assert "no_evidence" in issues_for([button(manual_evidence=None)])[0]


def test_evidence_matching_ignores_surrounding_whitespace():
    ok = button(manual_evidence={"page": 1, "quote": "  Nhấn nút Start để bắt đầu.  "})
    assert "no_evidence" not in issues_for([ok])[0]


def test_low_confidence_is_flagged_against_the_threshold():
    assert "low_confidence" in issues_for([button(confidence=0.4)])[0]
    assert "low_confidence" not in issues_for([button(confidence=0.5)])[0]
    assert "low_confidence" in issues_for([button(confidence=0.6)], confidence_threshold=0.7)[0]


def test_bbox_out_of_bounds_is_flagged():
    over = button(bbox_template_coordinates={"x": 950, "y": 0, "width": 100, "height": 10})
    assert "bbox_out_of_bounds" in issues_for([over])[0]
    negative = button(bbox_template_coordinates={"x": -1, "y": 0, "width": 10, "height": 10})
    assert "bbox_out_of_bounds" in issues_for([negative])[0]


def test_a_zero_width_bbox_is_out_of_bounds():
    flat = button(bbox_template_coordinates={"x": 10, "y": 10, "width": 0, "height": 10})
    assert "bbox_out_of_bounds" in issues_for([flat])[0]


def test_bbox_degenerate_is_flagged_below_the_area_ratio():
    # 0.1% of 1000x1000 is 1000 px. A 30x30 box is 900.
    tiny = button(bbox_template_coordinates={"x": 10, "y": 10, "width": 30, "height": 30})
    assert "bbox_degenerate" in issues_for([tiny])[0]
    just_big_enough = button(bbox_template_coordinates={"x": 10, "y": 10, "width": 32, "height": 32})
    assert "bbox_degenerate" not in issues_for([just_big_enough])[0]


def test_bbox_outside_panel_is_flagged_on_the_box_centre():
    panel = {"x": 0, "y": 0, "width": 500, "height": 500}
    outside = button(bbox_template_coordinates={"x": 600, "y": 600, "width": 100, "height": 100})
    checked, _ = run_qc([outside], manual_text=MANUAL, image=IMAGE, panel_bbox=panel)
    assert "bbox_outside_panel" in checked[0]["qc"]["issues"]


def test_bbox_outside_panel_is_skipped_when_there_is_no_panel():
    b = button(bbox_template_coordinates={"x": 600, "y": 600, "width": 100, "height": 100})
    checked, _ = run_qc([b], manual_text=MANUAL, image=IMAGE, panel_bbox=None)
    assert "bbox_outside_panel" not in checked[0]["qc"]["issues"]


def test_duplicate_id_flags_both_buttons_and_the_template():
    twins = [button(), button(bbox_template_coordinates={"x": 500, "y": 500, "width": 100, "height": 100})]
    checked, report = run_qc(twins, manual_text=MANUAL, image=IMAGE, panel_bbox=PANEL)
    assert all("duplicate_id" in b["qc"]["issues"] for b in checked)
    assert any(i["id"] == "duplicate_id" for i in report["template_issues"])


def test_two_null_ids_are_not_duplicates_of_each_other():
    nulls = [button(button_id=None), button(button_id=None, bbox_template_coordinates={"x": 500, "y": 500, "width": 100, "height": 100})]
    checked, _ = run_qc(nulls, manual_text=MANUAL, image=IMAGE, panel_bbox=PANEL)
    assert all("duplicate_id" not in b["qc"]["issues"] for b in checked)


def test_bbox_overlap_flags_both_buttons_above_the_threshold():
    a = button(button_id="a", bbox_template_coordinates={"x": 100, "y": 100, "width": 100, "height": 100})
    b = button(button_id="b", bbox_template_coordinates={"x": 150, "y": 100, "width": 100, "height": 100})
    checked, report = run_qc([a, b], manual_text=MANUAL, image=IMAGE, panel_bbox=PANEL)
    assert all("bbox_overlap" in x["qc"]["issues"] for x in checked)
    overlap = next(i for i in report["template_issues"] if i["id"] == "bbox_overlap")
    assert set(overlap["button_ids"]) == {"a", "b"}


def test_boxes_below_the_overlap_threshold_are_not_flagged():
    a = button(button_id="a", bbox_template_coordinates={"x": 100, "y": 100, "width": 100, "height": 100})
    b = button(button_id="b", bbox_template_coordinates={"x": 190, "y": 100, "width": 100, "height": 100})
    checked, _ = run_qc([a, b], manual_text=MANUAL, image=IMAGE, panel_bbox=PANEL)
    assert all("bbox_overlap" not in x["qc"]["issues"] for x in checked)


def test_manual_button_missing_is_a_template_issue():
    # The manual names Stop; detect never found it. Only the manual can reveal this.
    checked, report = run_qc([button()], manual_text=MANUAL, image=IMAGE, panel_bbox=PANEL)
    missing = next(i for i in report["template_issues"] if i["id"] == "manual_button_missing")
    assert "stop" in missing["names"]
    assert checked[0]["qc"]["status"] == "pass"  # a template issue does not fail a button


def test_detected_not_in_manual_is_a_template_issue():
    extra = button(button_id="grill", label_text="Grill", vietnamese_name="Nướng",
                   manual_evidence=None)
    _checked, report = run_qc([button(), extra], manual_text=MANUAL, image=IMAGE, panel_bbox=PANEL)
    not_in_manual = next(i for i in report["template_issues"] if i["id"] == "detected_not_in_manual")
    assert not_in_manual["button_ids"] == ["grill"]


def test_the_report_counts_passes_and_flags():
    _checked, report = run_qc(
        [button(), button(button_id="stop", vietnamese_name="",
                          bbox_template_coordinates={"x": 500, "y": 500, "width": 100, "height": 100},
                          manual_evidence={"page": 1, "quote": "Nhấn Stop để dừng."})],
        manual_text=MANUAL, image=IMAGE, panel_bbox=PANEL,
    )
    assert report["counts"] == {"total": 2, "pass": 1, "flag": 1}


def test_issues_are_sorted_so_the_report_is_stable():
    # Asserting the exact list, not `== sorted(itself)`, which would pass whatever
    # qc.py returned. The quote is in the manual, so no_evidence must not appear.
    bad = button(button_id="", vietnamese_name="", confidence=0.1)
    assert issues_for([bad])[0] == ["low_confidence", "missing_id", "missing_name"]
```

- [ ] **Step 2: Run the tests and watch them fail**

```bash
PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_label_qc.py
```

Expected: `ModuleNotFoundError: No module named 'scripts.label_pipeline.qc'`.

- [ ] **Step 3: Write `qc.py`**

Create `apps/vision-tools/scripts/label_pipeline/qc.py`:

```python
"""Stage 4: the single place that decides whether a button is trustworthy.

Flags, never deletes. Every detected button reaches the draft, because a button
silently dropped here is a button nobody reviews.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

from scripts.label_pipeline.geometry import bbox_area, center, iou

CONFIDENCE_THRESHOLD = 0.5
IOU_THRESHOLD = 0.3
MIN_AREA_RATIO = 0.001  # 0.1% of the image


def _fold(text: str) -> str:
    """Lowercase, strip diacritics. Used to compare model text against manual text."""
    folded = unicodedata.normalize("NFD", str(text or "").lower())
    return "".join(ch for ch in folded if not unicodedata.combining(ch))


def _mentions_raw_id(text: str, button_id: str) -> bool:
    # Word bounds, so "up" inside "Cúp điện" does not trip the rule.
    return re.search(rf"\b{re.escape(button_id)}\b", text, re.IGNORECASE) is not None


def _check_button(
    button: dict,
    *,
    manual_text: str,
    image: dict,
    panel_bbox: dict | None,
    confidence_threshold: float,
    min_area_ratio: float,
) -> list[str]:
    issues: list[str] = []
    button_id = (button.get("button_id") or "").strip()
    name = (button.get("vietnamese_name") or "").strip()

    if not button_id:
        issues.append("missing_id")
    if not name:
        issues.append("missing_name")

    if button_id:
        blob = f"{name} {button.get('function_description') or ''}"
        if _mentions_raw_id(blob, button_id):
            issues.append("raw_id_in_text")

    evidence = button.get("manual_evidence")
    raw_quote = evidence.get("quote") if isinstance(evidence, dict) else None
    # A non-string quote (Gemini can null the field inside an otherwise-present object)
    # counts as no quote. qc is the last gate before the draft: it flags, never crashes.
    quote = raw_quote.strip() if isinstance(raw_quote, str) else ""
    if not quote or _fold(quote) not in _fold(manual_text):
        issues.append("no_evidence")

    if float(button.get("confidence") or 0.0) < confidence_threshold:
        issues.append("low_confidence")

    box = button.get("bbox_template_coordinates") or {}
    if _out_of_bounds(box, image):
        issues.append("bbox_out_of_bounds")
    elif bbox_area(box) < min_area_ratio * image["width"] * image["height"]:
        issues.append("bbox_degenerate")

    if panel_bbox and box and not _center_inside(box, panel_bbox):
        issues.append("bbox_outside_panel")

    return issues


def _out_of_bounds(box: dict, image: dict) -> bool:
    if not box or box.get("width", 0) <= 0 or box.get("height", 0) <= 0:
        return True
    return (
        box["x"] < 0
        or box["y"] < 0
        or box["x"] + box["width"] > image["width"]
        or box["y"] + box["height"] > image["height"]
    )


def _center_inside(box: dict, panel: dict) -> bool:
    cx, cy = center(box)
    return (
        panel["x"] <= cx <= panel["x"] + panel["width"]
        and panel["y"] <= cy <= panel["y"] + panel["height"]
    )


def _manual_names(manual_text: str) -> set[str]:
    """Capitalised control names the manual mentions, folded and slugged, roughly.

    Deliberately crude: this feeds a flag, not a decision. Manuals omit minor buttons
    and photos crop corners, so both directions of this comparison only warn.
    """
    words = re.findall(r"\b[A-Z][a-zA-Z0-9]*(?:[ /-][A-Z][a-zA-Z0-9]*)*\b", manual_text)
    return {re.sub(r"[^a-z0-9]+", "_", w.lower()).strip("_") for w in words if len(w) > 1}


def run_qc(
    buttons: list[dict],
    *,
    manual_text: str,
    image: dict,
    panel_bbox: dict | None,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
    iou_threshold: float = IOU_THRESHOLD,
    min_area_ratio: float = MIN_AREA_RATIO,
) -> tuple[list[dict], dict]:
    per_button: list[list[str]] = [
        _check_button(
            b,
            manual_text=manual_text,
            image=image,
            panel_bbox=panel_bbox,
            confidence_threshold=confidence_threshold,
            min_area_ratio=min_area_ratio,
        )
        for b in buttons
    ]
    template_issues: list[dict] = []

    # duplicate_id — a null id is not a duplicate of another null id.
    seen: dict[str, list[int]] = defaultdict(list)
    for index, b in enumerate(buttons):
        button_id = (b.get("button_id") or "").strip()
        if button_id:
            seen[button_id].append(index)
    duplicates = {k: v for k, v in seen.items() if len(v) > 1}
    if duplicates:
        template_issues.append({"id": "duplicate_id", "button_ids": sorted(duplicates)})
        for indices in duplicates.values():
            for index in indices:
                per_button[index].append("duplicate_id")

    # bbox_overlap
    overlapping: set[int] = set()
    pairs: list[list[str | None]] = []
    for i in range(len(buttons)):
        for j in range(i + 1, len(buttons)):
            box_i = buttons[i].get("bbox_template_coordinates") or {}
            box_j = buttons[j].get("bbox_template_coordinates") or {}
            if box_i and box_j and iou(box_i, box_j) > iou_threshold:
                overlapping.update({i, j})
                pairs.append([buttons[i].get("button_id"), buttons[j].get("button_id")])
    if overlapping:
        template_issues.append(
            {
                "id": "bbox_overlap",
                "button_ids": sorted(str(buttons[i].get("button_id")) for i in overlapping),
                "pairs": pairs,
            }
        )
        for index in overlapping:
            per_button[index].append("bbox_overlap")

    # manual_button_missing / detected_not_in_manual — why the pipeline needs both inputs.
    detected_ids = {(b.get("button_id") or "").strip() for b in buttons} - {""}
    named_in_manual = _manual_names(manual_text)
    missing = sorted(named_in_manual - detected_ids - {"", "the"})
    unseen = sorted(
        button_id for button_id in detected_ids if button_id not in named_in_manual
    )
    if missing:
        template_issues.append({"id": "manual_button_missing", "names": missing})
    if unseen:
        template_issues.append({"id": "detected_not_in_manual", "button_ids": unseen})

    checked: list[dict] = []
    for b, issues in zip(buttons, per_button, strict=True):
        sorted_issues = sorted(set(issues))
        checked.append(
            {
                **b,
                "qc": {
                    "status": "pass" if not sorted_issues else "flag",
                    "issues": sorted_issues,
                    "confidence": float(b.get("confidence") or 0.0),
                },
            }
        )

    flagged = sum(1 for b in checked if b["qc"]["status"] == "flag")
    report = {
        "template_issues": template_issues,
        "counts": {"total": len(checked), "pass": len(checked) - flagged, "flag": flagged},
    }
    return checked, report
```

- [ ] **Step 4: Run the tests and watch them pass**

```bash
PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_label_qc.py
```

Expected: `27 passed`.

`_manual_names` is crude by design. If `test_manual_button_missing_is_a_template_issue` or `test_detected_not_in_manual_is_a_template_issue` fails, print `_manual_names(MANUAL)` and adjust the regex until `{"start", "stop", "nhan"}`-ish comes out. Do not tighten it beyond what makes the two tests pass — it feeds a warning, not a gate.

- [ ] **Step 5: Commit**

```bash
ruff check apps/vision-tools/scripts/label_pipeline apps/vision-tools/tests/test_label_qc.py
git add apps/vision-tools/scripts/label_pipeline/qc.py apps/vision-tools/tests/test_label_qc.py
git commit -m "feat(label-pipeline): flag every button a human must recheck

Flags, never deletes: a button dropped here is a button nobody reviews.

raw_id_in_text mirrors a bug already fixed on the API side, where the LLM
echoed time_1_min into spoken text and gTTS read it aloud as 'tam gach duoi
mot gach duoi min'. It matches on word bounds so 'up' inside a Vietnamese
word does not trip it.

manual_button_missing and detected_not_in_manual are why the pipeline needs
both inputs: the image cannot reveal a missing button, and the manual cannot
say where a button is. Both only warn."
```

---

## Task 7: `pipeline.py` — compose and emit the draft

**Files:**
- Create: `apps/vision-tools/scripts/label_pipeline/pipeline.py`
- Create: `apps/vision-tools/tests/test_label_pipeline.py`
- Create: `data/manuals/.gitkeep`

**Interfaces:**
- Consumes: every stage.
- Produces:
  - `build_draft(*, detections, qc_buttons, device, template) -> dict` — pure; assembles the label JSON.
    `described` is deliberately absent: `_merge` folds the descriptions into `qc_buttons`
    before `run_qc` sees them, so `build_draft` would never read it.
  - `run(args: argparse.Namespace, *, client: GeminiClient) -> dict`
  - `main(argv: list[str] | None = None) -> int`

The draft must match the schema `seed.py` already reads: top-level `device`, `template`, `buttons`; each button carrying `id`, `template_id`, `button_id`, `label`, `vietnamese_name`, `function_description`, `bbox_template_coordinates`, `polygon_template_coordinates`, `button_type`, plus the new `qc`. `seed.py` inserts by column name and ignores `qc`.

- [ ] **Step 1: Write the failing tests**

Create `apps/vision-tools/tests/test_label_pipeline.py`:

```python
from __future__ import annotations

import json

from scripts.label_pipeline.pipeline import build_draft

DEVICE = {
    "id": "device_panasonic_microwave_nn_gt35hm",
    "brand": "Panasonic",
    "appliance_type": "microwave",
    "model_name": "NN-GT35HM",
    "display_name": "Lò vi sóng Panasonic NN-GT35HM",
    "status": "active",
}
TEMPLATE = {
    "id": "template_panasonic_microwave_nn_gt35hm_v1",
    "device_id": DEVICE["id"],
    "template_code": "panasonic_microwave_nn_gt35hm_v1",
    "template_image_url": "data/templates/panasonic_microwave_nn_gt35hm.png",
    "version": 1,
    "status": "draft",
}
DETECTIONS = {
    "image": {"width": 5712, "height": 4284},
    "regions": {"logo": {"x": 1, "y": 2, "width": 3, "height": 4}, "panel": None},
    "detections": [
        {
            "button_id": "start",
            "label_text": "Start",
            "bbox_template_coordinates": {"x": 10, "y": 10, "width": 50, "height": 50},
            "confidence": 0.9,
        }
    ],
}
QC_BUTTONS = [
    {
        "button_id": "start",
        "label_text": "Start",
        "vietnamese_name": "Bắt đầu",
        "function_description": "bắt đầu nấu",
        "manual_evidence": {"page": 1, "quote": "Nhấn Start."},
        "bbox_template_coordinates": {"x": 10, "y": 10, "width": 50, "height": 50},
        "confidence": 0.9,
        "qc": {"status": "pass", "issues": [], "confidence": 0.9},
    }
]


def test_the_draft_has_the_three_top_level_blocks_seed_expects():
    draft = build_draft(
        detections=DETECTIONS, qc_buttons=QC_BUTTONS, device=DEVICE, template=TEMPLATE,
    )
    assert set(draft) == {"device", "template", "buttons"}


def test_each_button_carries_the_columns_seed_inserts():
    draft = build_draft(detections=DETECTIONS, qc_buttons=QC_BUTTONS,
                        device=DEVICE, template=TEMPLATE)
    button = draft["buttons"][0]
    for key in ("id", "template_id", "button_id", "label", "vietnamese_name",
                "function_description", "bbox_template_coordinates",
                "polygon_template_coordinates", "button_type"):
        assert key in button, key


def test_the_button_row_id_follows_the_shipped_naming():
    draft = build_draft(detections=DETECTIONS, qc_buttons=QC_BUTTONS,
                        device=DEVICE, template=TEMPLATE)
    assert draft["buttons"][0]["id"] == "btn_panasonic_microwave_nn_gt35hm_v1_start"
    assert draft["buttons"][0]["template_id"] == TEMPLATE["id"]


def test_qc_rides_inside_the_button_so_label_web_reads_one_file():
    draft = build_draft(detections=DETECTIONS, qc_buttons=QC_BUTTONS,
                        device=DEVICE, template=TEMPLATE)
    assert draft["buttons"][0]["qc"]["status"] == "pass"


def test_the_detected_regions_populate_logo_and_panel_bbox():
    draft = build_draft(detections=DETECTIONS, qc_buttons=QC_BUTTONS,
                        device=DEVICE, template=TEMPLATE)
    assert draft["template"]["logo_bbox"] == {"x": 1, "y": 2, "width": 3, "height": 4}
    assert draft["template"]["panel_bbox"] is None


def test_a_null_id_button_gets_a_row_id_from_its_index_not_from_none():
    qc_buttons = [{**QC_BUTTONS[0], "button_id": None, "label_text": ""}]
    draft = build_draft(detections=DETECTIONS, qc_buttons=qc_buttons,
                        device=DEVICE, template=TEMPLATE)
    assert draft["buttons"][0]["id"].endswith("_unnamed_0")
    assert draft["buttons"][0]["button_id"] == ""


def test_the_draft_is_json_serialisable_without_ascii_escaping():
    draft = build_draft(detections=DETECTIONS, qc_buttons=QC_BUTTONS,
                        device=DEVICE, template=TEMPLATE)
    text = json.dumps(draft, ensure_ascii=False)
    assert "Bắt đầu" in text


def test_the_draft_button_type_defaults_to_touch():
    draft = build_draft(detections=DETECTIONS, qc_buttons=QC_BUTTONS,
                        device=DEVICE, template=TEMPLATE)
    assert draft["buttons"][0]["button_type"] == "touch"
```

- [ ] **Step 2: Run the tests and watch them fail**

```bash
PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_label_pipeline.py
```

Expected: `ModuleNotFoundError: No module named 'scripts.label_pipeline.pipeline'`.

- [ ] **Step 3: Write `pipeline.py`**

Create `apps/vision-tools/scripts/label_pipeline/pipeline.py`:

```python
"""Composes the four stages and writes <template_code>.draft.json + qc_report.json.

The pipeline never overwrites a reviewed label file. It writes a draft; a human
renames it after review. Nothing here writes to apps/api/silvertech.sqlite3.

Usage:
    PYTHONPATH=apps/vision-tools python -m scripts.label_pipeline.pipeline \\
      --manual data/manuals/panasonic_nn_gt35hm.pdf \\
      --image  data/templates/panasonic_microwave_nn_gt35hm.png \\
      --brand Panasonic --model-name NN-GT35HM --appliance-type microwave \\
      --display-name "Lò vi sóng Panasonic NN-GT35HM" \\
      --out data/templates/labels/panasonic_microwave_nn_gt35hm_v1.draft.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.label_pipeline.describe import write_descriptions
from scripts.label_pipeline.detect import slug, write_detections
from scripts.label_pipeline.extract import manual_full_text, write_manual_text
from scripts.label_pipeline.gemini_client import (
    DEFAULT_MODEL,
    GeminiClient,
    GeminiError,
    load_api_key,
)
from scripts.label_pipeline.qc import run_qc

DEFAULT_BUTTON_TYPE = "touch"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_draft(
    *,
    detections: dict,
    qc_buttons: list[dict],
    device: dict,
    template: dict,
) -> dict:
    # label_web/app.js:286 builds the row id from the template code, _v1 included,
    # and recomputes it on every save. Diverge and the first save renames every row.
    code = template["template_code"]
    rows: list[dict] = []
    for index, button in enumerate(qc_buttons):
        button_id = (button.get("button_id") or "").strip()
        suffix = button_id or f"unnamed_{index}"
        rows.append(
            {
                "id": f"btn_{code}_{suffix}",
                "template_id": template["id"],
                "button_id": button_id,
                "label": button.get("label_text") or button_id,
                "vietnamese_name": button.get("vietnamese_name", ""),
                "function_description": button.get("function_description", ""),
                "bbox_template_coordinates": button["bbox_template_coordinates"],
                "polygon_template_coordinates": None,
                "button_type": button.get("button_type") or DEFAULT_BUTTON_TYPE,
                "created_at": _now(),
                "updated_at": _now(),
                "qc": button["qc"],
            }
        )
    regions = detections.get("regions") or {}
    return {
        "device": {**device, "created_at": _now(), "updated_at": _now()},
        "template": {
            # seed.py binds :feature_descriptor_path; omitting it fails the insert.
            "feature_descriptor_path": None,
            **template,
            "logo_bbox": regions.get("logo"),
            "panel_bbox": regions.get("panel"),
            "created_at": _now(),
            "updated_at": _now(),
        },
        "buttons": rows,
    }


def _merge(detections: dict, described: dict) -> list[dict]:
    # Skip null ids: otherwise every icon-only button would share one description.
    by_id = {b["button_id"]: b for b in described["buttons"] if b.get("button_id")}
    merged: list[dict] = []
    for detection in detections["detections"]:
        button_id = detection["button_id"]
        description = by_id.get(button_id, {}) if button_id else {}
        merged.append(
            {
                "button_id": detection["button_id"],
                "label_text": detection["label_text"],
                "bbox_template_coordinates": detection["bbox_template_coordinates"],
                "confidence": detection["confidence"],
                "vietnamese_name": description.get("vietnamese_name", ""),
                "function_description": description.get("function_description", ""),
                "manual_evidence": description.get("manual_evidence"),
            }
        )
    return merged


def run(args: argparse.Namespace, *, client: GeminiClient) -> dict:
    out_path = Path(args.out)
    work_dir = out_path.parent / ".pipeline" / Path(args.image).stem
    work_dir.mkdir(parents=True, exist_ok=True)

    manual_text = write_manual_text(
        Path(args.manual), work_dir / "manual_text.json", client=client
    )
    detections = write_detections(
        Path(args.image), work_dir / "detections.json", client=client
    )
    described = write_descriptions(
        manual_text, detections, work_dir / "described.json", client=client
    )

    qc_buttons, report = run_qc(
        _merge(detections, described),
        manual_text=manual_full_text(manual_text),
        image=detections["image"],
        panel_bbox=(detections.get("regions") or {}).get("panel"),
        confidence_threshold=args.confidence_threshold,
    )

    template_code = args.template_code or (
        slug(f"{args.brand} {args.appliance_type} {args.model_name}") + "_v1"
    )
    device = {
        "id": f"device_{template_code.removesuffix('_v1')}",
        "brand": args.brand,
        "appliance_type": args.appliance_type,
        "model_name": args.model_name,
        "display_name": args.display_name or f"{args.brand} {args.model_name}",
        "status": "active",
    }
    template = {
        "id": f"template_{template_code}",
        "device_id": device["id"],
        "template_code": template_code,
        "template_image_url": args.image,
        "feature_descriptor_path": None,
        "version": 1,
        "status": "draft",
    }

    draft = build_draft(
        detections=detections, qc_buttons=qc_buttons, device=device, template=template,
    )

    # Never overwrite a reviewed label file.
    if out_path.exists() and not out_path.name.endswith(".draft.json"):
        raise SystemExit(f"refusing to overwrite reviewed label file {out_path}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")

    report_path = out_path.with_name(out_path.name.replace(".draft.json", ".qc_report.json"))
    report = {**report, "draft": str(out_path), "model": client.model}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    counts = report["counts"]
    print(f"{out_path}: {counts['total']} buttons, {counts['flag']} flagged")
    for issue in report["template_issues"]:
        print(f"  template: {issue['id']}")
    return draft


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manual", required=True, help="appliance manual PDF")
    parser.add_argument("--image", required=True, help="control panel image")
    parser.add_argument("--out", required=True, help="path ending in .draft.json")
    parser.add_argument("--brand", required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--appliance-type", required=True)
    parser.add_argument("--display-name", default=None)
    parser.add_argument("--template-code", default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--confidence-threshold", type=float, default=0.5)
    args = parser.parse_args(argv)

    if not args.out.endswith(".draft.json"):
        parser.error("--out must end in .draft.json; a human renames it after review")

    try:
        client = GeminiClient(api_key=load_api_key(), model=args.model)
        run(args, client=client)
    except (GeminiError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests and watch them pass**

```bash
PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_label_pipeline.py
```

Expected: `11 passed`.

- [ ] **Step 5: Check the CLI refuses to clobber a reviewed file**

```bash
PYTHONPATH=apps/vision-tools python -m scripts.label_pipeline.pipeline \
  --manual x.pdf --image y.png --out data/templates/labels/panasonic_microwave_nn_gt35hm_v1.json \
  --brand P --model-name M --appliance-type microwave
```

Expected: exit 2, `--out must end in .draft.json; a human renames it after review`.

- [ ] **Step 6: Create the manuals directory**

```bash
mkdir -p data/manuals && touch data/manuals/.gitkeep
```

- [ ] **Step 7: Commit**

```bash
ruff check apps/vision-tools/scripts/label_pipeline apps/vision-tools/tests/test_label_pipeline.py
git add apps/vision-tools/scripts/label_pipeline/pipeline.py \
        apps/vision-tools/tests/test_label_pipeline.py data/manuals/.gitkeep
git commit -m "feat(label-pipeline): compose the stages into a draft label file

The output is <template_code>.draft.json in the schema seed.py already reads,
plus a qc field per button that seed.py ignores because it inserts by column
name. label_web then paints its warnings from one file.

The CLI refuses any --out that is not a .draft.json: a reviewed label file is
a human artifact and the pipeline may not overwrite one."
```

---

## Task 8: `eval_detect.py` — measure detect against the gold set

Read the "Corrections to the spec's evaluation section" above before starting. Two of the spec's numbers are wrong and one of its metrics is not measurable on half the gold set.

**Files:**
- Create: `apps/vision-tools/scripts/label_pipeline/eval_detect.py`
- Create: `apps/vision-tools/tests/test_label_eval_detect.py`

**Interfaces:**
- Consumes: `iou` (Task 1).
- Produces:
  - `match_greedy(detections: list[dict], gold: list[dict], *, threshold: float = 0.5) -> list[Match]`
  - `class Match(NamedTuple)`: `detection_index: int | None`, `gold_index: int | None`, `score: float`
  - `evaluate(detections: list[dict], gold: list[dict], *, threshold: float = 0.5) -> dict`
  - `main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: Write the failing tests**

Create `apps/vision-tools/tests/test_label_eval_detect.py`:

```python
from __future__ import annotations

import pytest

from scripts.label_pipeline.eval_detect import evaluate, match_greedy


def box(x, y, size=100):
    return {"x": x, "y": y, "width": size, "height": size}


def det(button_id, x, y, size=100):
    return {"button_id": button_id, "bbox_template_coordinates": box(x, y, size)}


def test_a_perfect_match_scores_one_across_the_board():
    gold = [det("start", 0, 0), det("stop", 200, 0)]
    result = evaluate(list(gold), gold)
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["mean_iou"] == pytest.approx(1.0)
    assert result["id_accuracy"] == 1.0


def test_an_extra_detection_lowers_precision_but_not_recall():
    gold = [det("start", 0, 0)]
    detections = [det("start", 0, 0), det("ghost", 500, 500)]
    result = evaluate(detections, gold)
    assert result["precision"] == 0.5
    assert result["recall"] == 1.0


def test_a_missed_button_lowers_recall_but_not_precision():
    gold = [det("start", 0, 0), det("up", 200, 0)]
    result = evaluate([det("start", 0, 0)], gold)
    assert result["precision"] == 1.0
    assert result["recall"] == 0.5


def test_a_box_below_the_iou_threshold_is_not_a_match():
    gold = [det("start", 0, 0)]
    result = evaluate([det("start", 80, 0)], gold)  # IoU 0.11
    assert result["recall"] == 0.0
    assert result["matched"] == 0


def test_matching_is_one_to_one_and_takes_the_best_pair_first():
    gold = [det("start", 0, 0)]
    detections = [det("a", 10, 0), det("b", 0, 0)]  # b is the tighter box
    matches = [m for m in match_greedy(detections, gold) if m.gold_index is not None
               and m.detection_index is not None]
    assert len(matches) == 1
    assert detections[matches[0].detection_index]["button_id"] == "b"


def test_id_accuracy_counts_only_matched_pairs():
    gold = [det("start", 0, 0), det("stop", 200, 0)]
    detections = [det("start", 0, 0), det("wrong_name", 200, 0)]
    result = evaluate(detections, gold)
    assert result["recall"] == 1.0
    assert result["id_accuracy"] == 0.5


def test_numeric_gold_ids_are_excluded_from_id_accuracy():
    # Electrolux ids are "1".."11": position numbers off a manual diagram, not slugs
    # of on-panel text. No slug will ever equal "7", so scoring against them would
    # drag the metric down for a reason unrelated to the model.
    gold = [det("start", 0, 0), det("7", 200, 0)]
    detections = [det("start", 0, 0), det("power", 200, 0)]
    result = evaluate(detections, gold)
    assert result["id_accuracy"] == 1.0
    assert result["id_accuracy_excluded"] == 1


def test_id_accuracy_is_none_when_every_gold_id_is_numeric():
    gold = [det("1", 0, 0)]
    result = evaluate([det("power", 0, 0)], gold)
    assert result["id_accuracy"] is None
    assert result["id_accuracy_excluded"] == 1


def test_a_null_detected_id_never_matches_a_gold_id():
    gold = [det("up", 0, 0)]
    detections = [{"button_id": None, "bbox_template_coordinates": box(0, 0)}]
    result = evaluate(detections, gold)
    assert result["recall"] == 1.0  # the box is right
    assert result["id_accuracy"] == 0.0  # the id is absent


def test_mean_iou_averages_only_matched_pairs():
    # The second box overlaps by 80/100, giving IoU 8000/12000 = 2/3. It must stay
    # above the 0.5 match threshold, or there is nothing to average.
    gold = [det("start", 0, 0), det("stop", 500, 0)]
    detections = [det("start", 0, 0), det("stop", 520, 0)]
    result = evaluate(detections, gold)
    assert result["mean_iou"] == pytest.approx((1.0 + 2 / 3) / 2)


def test_an_empty_detection_list_scores_zero_without_dividing_by_zero():
    result = evaluate([], [det("start", 0, 0)])
    assert result["precision"] == 0.0
    assert result["recall"] == 0.0
    assert result["mean_iou"] == 0.0
    assert result["id_accuracy"] is None


def test_the_per_button_table_names_every_gold_button():
    # With n=27, one button is 4%. The aggregates alone would be self-deception.
    gold = [det("start", 0, 0), det("up", 500, 0)]
    result = evaluate([det("start", 0, 0)], gold)
    rows = {row["gold_id"]: row for row in result["per_button"]}
    assert set(rows) == {"start", "up"}
    assert rows["up"]["status"] == "missed"
    assert rows["start"]["status"] == "matched"
    assert rows["start"]["iou"] == pytest.approx(1.0)


def test_the_per_button_table_lists_extra_detections():
    gold = [det("start", 0, 0)]
    result = evaluate([det("start", 0, 0), det("ghost", 900, 900)], gold)
    extra = [row for row in result["per_button"] if row["status"] == "extra"]
    assert extra[0]["detected_id"] == "ghost"
    assert extra[0]["gold_id"] is None
```

- [ ] **Step 2: Run the tests and watch them fail**

```bash
PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_label_eval_detect.py
```

Expected: `ModuleNotFoundError: No module named 'scripts.label_pipeline.eval_detect'`.

- [ ] **Step 3: Write `eval_detect.py`**

Create `apps/vision-tools/scripts/label_pipeline/eval_detect.py`:

```python
"""Measure detect.py against the two reviewed label files.

Run by hand, never in CI: CI calling the Gemini API would burn the free-tier quota.

Precision, recall and mean IoU measure three different things. A model can reach 100%
recall with a mean IoU of 0.55 -- it sees every button and boxes them loosely.
Collapsing them into one score hides that.

Gold set: Panasonic (16 buttons) + Electrolux (11) = 27. Electrolux's button_ids are
"1".."11" -- position numbers from a manual diagram, not slugs of on-panel text. They
are excluded from id_accuracy, and the excluded count is printed so the number is never
read as though it covered all 27.

Usage:
    PYTHONPATH=apps/vision-tools python -m scripts.label_pipeline.eval_detect \\
      --detections .cache/detections.json \\
      --gold data/templates/labels/panasonic_microwave_nn_gt35hm_v1.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import NamedTuple

from scripts.label_pipeline.geometry import iou

IOU_THRESHOLD = 0.5


class Match(NamedTuple):
    detection_index: int | None
    gold_index: int | None
    score: float


def _is_positional_id(button_id: str) -> bool:
    """An id like "7" names a diagram callout, not any text printed on the panel."""
    return bool(re.fullmatch(r"\d+", str(button_id or "").strip()))


def match_greedy(
    detections: list[dict], gold: list[dict], *, threshold: float = IOU_THRESHOLD
) -> list[Match]:
    pairs = sorted(
        (
            (iou(d["bbox_template_coordinates"], g["bbox_template_coordinates"]), di, gi)
            for di, d in enumerate(detections)
            for gi, g in enumerate(gold)
        ),
        reverse=True,
    )
    used_d: set[int] = set()
    used_g: set[int] = set()
    matches: list[Match] = []
    for score, di, gi in pairs:
        if score <= threshold or di in used_d or gi in used_g:
            continue
        used_d.add(di)
        used_g.add(gi)
        matches.append(Match(di, gi, score))
    matches += [Match(None, gi, 0.0) for gi in range(len(gold)) if gi not in used_g]
    matches += [Match(di, None, 0.0) for di in range(len(detections)) if di not in used_d]
    return matches


def evaluate(
    detections: list[dict], gold: list[dict], *, threshold: float = IOU_THRESHOLD
) -> dict:
    matches = match_greedy(detections, gold, threshold=threshold)
    matched = [m for m in matches if m.detection_index is not None and m.gold_index is not None]

    id_hits = 0
    id_scored = 0
    excluded = sum(1 for g in gold if _is_positional_id(g["button_id"]))
    per_button: list[dict] = []

    for m in matches:
        gold_button = gold[m.gold_index] if m.gold_index is not None else None
        detection = detections[m.detection_index] if m.detection_index is not None else None
        if gold_button is not None and detection is not None:
            status = "matched"
            if not _is_positional_id(gold_button["button_id"]):
                id_scored += 1
                id_hits += int(detection["button_id"] == gold_button["button_id"])
        elif gold_button is not None:
            status = "missed"
        else:
            status = "extra"
        per_button.append(
            {
                "gold_id": gold_button["button_id"] if gold_button else None,
                "detected_id": detection["button_id"] if detection else None,
                "iou": round(m.score, 3),
                "status": status,
            }
        )

    per_button.sort(key=lambda row: (row["status"] != "matched", row["gold_id"] or "~"))
    return {
        "threshold": threshold,
        "gold_count": len(gold),
        "detected_count": len(detections),
        "matched": len(matched),
        "precision": len(matched) / len(detections) if detections else 0.0,
        "recall": len(matched) / len(gold) if gold else 0.0,
        "mean_iou": sum(m.score for m in matched) / len(matched) if matched else 0.0,
        "id_accuracy": (id_hits / id_scored) if id_scored else None,
        "id_accuracy_scored": id_scored,
        "id_accuracy_excluded": excluded,
        "per_button": per_button,
    }


def _print(result: dict) -> None:
    print(f"gold {result['gold_count']}  detected {result['detected_count']}  "
          f"matched {result['matched']}  @IoU>{result['threshold']}")
    print(f"precision {result['precision']:.2f}   recall {result['recall']:.2f}   "
          f"mean IoU {result['mean_iou']:.2f}")
    if result["id_accuracy"] is None:
        print(f"button_id accuracy: n/a ({result['id_accuracy_excluded']} positional gold ids)")
    else:
        print(f"button_id accuracy {result['id_accuracy']:.2f} "
              f"over {result['id_accuracy_scored']} pairs "
              f"({result['id_accuracy_excluded']} positional gold ids excluded)")
    print()
    print(f"{'gold_id':<20} {'detected_id':<20} {'IoU':>6}  status")
    for row in result["per_button"]:
        print(f"{str(row['gold_id']):<20} {str(row['detected_id']):<20} "
              f"{row['iou']:>6.3f}  {row['status']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--detections", required=True, help="detections.json from detect.py")
    parser.add_argument("--gold", required=True, help="a reviewed label JSON file")
    parser.add_argument("--threshold", type=float, default=IOU_THRESHOLD)
    args = parser.parse_args(argv)

    detections = json.loads(Path(args.detections).read_text(encoding="utf-8"))["detections"]
    gold = json.loads(Path(args.gold).read_text(encoding="utf-8"))["buttons"]
    _print(evaluate(detections, gold, threshold=args.threshold))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests and watch them pass**

```bash
PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_label_eval_detect.py
```

Expected: `13 passed`.

- [ ] **Step 5: Confirm the eval reads a real gold file**

Self-evaluation: feed the gold file to itself. Everything must be 1.0.

```bash
PYTHONPATH=apps/vision-tools python -c "
import json
from scripts.label_pipeline.eval_detect import evaluate
gold = json.load(open('data/templates/labels/panasonic_microwave_nn_gt35hm_v1.json'))['buttons']
r = evaluate(gold, gold)
print('panasonic self-eval:', r['precision'], r['recall'], round(r['mean_iou'],3), r['id_accuracy'])
assert (r['precision'], r['recall'], r['id_accuracy']) == (1.0, 1.0, 1.0)
elx = json.load(open('data/templates/labels/electrolux_washer_ewf9024adsa_v1.json'))['buttons']
r = evaluate(elx, elx)
print('electrolux self-eval: id_accuracy', r['id_accuracy'], 'excluded', r['id_accuracy_excluded'])
assert r['id_accuracy'] is None and r['id_accuracy_excluded'] == 11
print('OK')
"
```

Expected: `panasonic self-eval: 1.0 1.0 1.0 1.0`, then `electrolux self-eval: id_accuracy None excluded 11`, then `OK`.

The Electrolux line is the point: its ids are positional, so id accuracy is `None` even when the detections are literally the gold file.

- [ ] **Step 6: Run the whole suite and commit**

```bash
PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests
ruff check apps/vision-tools/scripts/label_pipeline apps/vision-tools/tests
```

Expected: all existing vision tests plus the new ones pass.

```bash
git add apps/vision-tools/scripts/label_pipeline/eval_detect.py \
        apps/vision-tools/tests/test_label_eval_detect.py
git commit -m "feat(label-pipeline): score detections against the reviewed labels

Precision, recall and mean IoU measure three different things; a model can
reach full recall with a mean IoU of 0.55. They are reported separately, with
a per-button table, because at n=27 one button is 4% and the aggregates alone
would be self-deception.

Electrolux button_ids are position numbers from a manual diagram, not slugs of
on-panel text, so no slug can ever equal them. They are excluded from
button_id accuracy and the excluded count is printed alongside it."
```

---

## Task 9: Document the pipeline

**Files:**
- Create: `docs/label-qa-pipeline.md`
- Modify: `CLAUDE.md`
- Modify: `Makefile`

**Interfaces:**
- Consumes: everything.
- Produces: a `make test-label` target and a doc a new operator can follow.

- [ ] **Step 1: Write the doc**

Create `docs/label-qa-pipeline.md`:

```markdown
# Label QA/QC pipeline

Turns an appliance manual PDF and a control-panel photo into a *draft* label file:
one bounding box and one Vietnamese description per button, with a QC flag on every
button a human must re-check.

It emits a proposal. A human still reviews it. Nothing here writes to the database.

## Run it

```bash
conda activate silvertech
export GEMINI_API_KEY=...            # or put it in .env

PYTHONPATH=apps/vision-tools python -m scripts.label_pipeline.pipeline \
  --manual data/manuals/panasonic_nn_gt35hm.pdf \
  --image  data/templates/panasonic_microwave_nn_gt35hm.png \
  --brand Panasonic --model-name NN-GT35HM --appliance-type microwave \
  --display-name "Lò vi sóng Panasonic NN-GT35HM" \
  --out data/templates/labels/panasonic_microwave_nn_gt35hm_v1.draft.json
```

Then open the draft in `label_web/`, fix every button whose `qc.status` is `flag`,
and rename the file to drop `.draft`. Only then does `make seed-api` see it.

The CLI refuses an `--out` that is not a `.draft.json`. A reviewed label file is a
human artifact.

## Stages

| Stage | In | Out | Network |
|---|---|---|---|
| `extract` | manual PDF | `manual_text.json` | only for scanned pages |
| `detect` | panel image | `detections.json` | one call |
| `describe` | manual text + ids | `described.json` | one call |
| `qc` | the above | `*.draft.json`, `*.qc_report.json` | none |

Intermediates land in `<out_dir>/.pipeline/<image_stem>/`. `detect` does not know the
manual exists; `describe` does not know the image exists. They meet only through
`button_id`.

## Cost

Every Gemini call is cached under `.cache/label_pipeline/`, keyed by the model, a hash
of the prompt, and a hash of the image. Re-running after editing a QC rule costs zero
requests. Editing a prompt invalidates only that prompt's entries.

## QC flags

Per button: `missing_id`, `missing_name`, `raw_id_in_text`, `no_evidence`,
`low_confidence`, `bbox_out_of_bounds`, `bbox_degenerate`, `bbox_outside_panel`.

Per template: `duplicate_id`, `bbox_overlap`, `manual_button_missing`,
`detected_not_in_manual`.

QC flags; it never deletes. A button dropped here is a button nobody reviews.

`raw_id_in_text` exists because the API once fed a raw `button_id` to TTS, and gTTS
read `time_1_min` aloud as "tam gạch dưới một gạch dưới min".

`manual_button_missing` and `detected_not_in_manual` are why the pipeline needs both
inputs: the image cannot reveal a button that is missing, and the manual cannot say
where a button is. Both only warn — manuals omit minor buttons, and photos crop corners.

## Measuring detect

```bash
PYTHONPATH=apps/vision-tools python -m scripts.label_pipeline.eval_detect \
  --detections data/templates/labels/.pipeline/panasonic_microwave_nn_gt35hm/detections.json \
  --gold data/templates/labels/panasonic_microwave_nn_gt35hm_v1.json
```

Reports precision, recall, mean IoU and `button_id` accuracy separately, plus a
per-button table. They measure different things: a model can reach full recall with a
mean IoU of 0.55, seeing every button and boxing them loosely.

There is no pass/fail threshold. "Good enough" means correcting the draft is cheaper
than labeling from scratch. Run it by hand — in CI it would burn the free-tier quota.

Electrolux's `button_id`s are `"1"`…`"11"`: position numbers from a manual diagram,
not slugs of panel text. They are excluded from `button_id` accuracy, and the excluded
count is printed beside it.

## Limitations

- `pypdf` cannot rasterize. A scanned page is OCR'd from its largest embedded image; a
  page with none is recorded as an error and skipped.
- `data/manuals/` ships empty. Add the manual PDF before the first run.
- `brand`, `model_name` and `appliance_type` come from CLI flags, not from the manual
  cover page.
```

- [ ] **Step 2: Add the Makefile target**

In `Makefile`, next to `test-vision`:

```make
test-label:
	PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_label_geometry.py \
	  apps/vision-tools/tests/test_label_gemini_client.py \
	  apps/vision-tools/tests/test_label_extract.py \
	  apps/vision-tools/tests/test_label_detect.py \
	  apps/vision-tools/tests/test_label_describe.py \
	  apps/vision-tools/tests/test_label_qc.py \
	  apps/vision-tools/tests/test_label_pipeline.py \
	  apps/vision-tools/tests/test_label_eval_detect.py
```

Add `test-label` to the `.PHONY` line if one exists.

- [ ] **Step 3: Point CLAUDE.md at the doc**

In `CLAUDE.md`, under the `apps/vision-tools` bullet in the Architecture section, append a sentence:

```markdown
It also hosts the offline label QA/QC pipeline (`scripts/label_pipeline/`), which turns a
manual PDF plus a panel photo into a draft label file with per-button QC flags — see
`docs/label-qa-pipeline.md`. It calls Gemini and is never imported by the API.
```

- [ ] **Step 4: Verify the target runs**

```bash
make test-label
```

Expected: `114 passed` (12 + 24 + 8 + 11 + 7 + 27 + 11 + 13) — 114 today, 127 once Task 8 lands.

- [ ] **Step 5: Commit**

```bash
git add docs/label-qa-pipeline.md Makefile CLAUDE.md
git commit -m "docs(label-pipeline): document the pipeline and add make test-label"
```

---

## First real run

Not a task — there is no manual PDF in the repo yet, so this cannot be scripted. Do it once a manual lands in `data/manuals/`.

1. Run the pipeline on the Panasonic microwave.
2. Run `eval_detect` against `panasonic_microwave_nn_gt35hm_v1.json`.
3. **Check the spec's recorded prediction**: the model should miss the icon-only `up` and `down` arrows, and `button_id` accuracy should land below recall, because those two buttons carry no text to slug.

If both hold, the design's model of the problem is sound. **If they do not hold, stop and re-read the spec's assumptions** — something in it is wrong, and the numbers will be measuring something other than what they claim.

Record the three aggregates and the per-button table in the PR description. At n=27 a single button moves any aggregate by 4%, so the table is the evidence and the aggregates are the summary.
