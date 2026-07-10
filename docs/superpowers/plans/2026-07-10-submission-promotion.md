# Submission Promotion & Admin Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn a reviewed user submission into a template the vision pipeline can actually detect, and give an admin a page to review one.

**Architecture:** A new `promotion_service` inserts `devices` + `templates` + `buttons` + `button_offsets` inside the caller's transaction. `review_service` calls it on `accept`/`edit`. The `/api/admin` router moves behind a shared-secret header and gains two read endpoints. `label_web/` gets a second page that lists pending submissions and posts the review.

**Tech Stack:** Python 3.12, FastAPI, raw `sqlite3`, pytest. Plain-script JS (no bundler, no modules) for `label_web/`.

Design: `docs/superpowers/specs/2026-07-10-submission-promotion-design.md`

## Global Constraints

- Work on branch `004-submission-promotion`. It is already checked out, rebased
  onto a `main` whose suite is green: **173 passed** across `apps/api/tests`,
  `tests/contract` and `apps/vision-tools/tests`. Any red test you see is yours.
- Always run inside the `silvertech` conda env: `conda activate silvertech`.
  Without it `ruff` is not on `PATH` and `python` has no `gTTS` or `cv2`.
- Tests need `PYTHONPATH` — packages run via path, not install.
  API tests: `PYTHONPATH=apps/api pytest -q apps/api/tests`
  Contract tests: `PYTHONPATH=apps/api pytest -q tests/contract`
  The detectability test also needs `apps/vision-tools` on the path.
- The `rtk` shell hook mangles command output. Prefix every `pytest`, `ruff`,
  `git`, `grep` and `sed` invocation with `rtk proxy`, or the result you read
  will not be the result that happened.
- Lint: `rtk proxy ruff check apps/api`, currently clean. `line-length = 100`,
  but `E501` is not in the selected rule set, so ruff will not flag a long line;
  keep to 100 by hand. It **does** flag `F401`, so add each import in the task
  that first uses it — a module written ahead of its imports fails the commit.
- `database_path()` reads `SILVERTECH_DB_PATH` on every call, so a fixture that
  repoints it really does get its own database. Row-count assertions are safe.
- User-facing error strings in this repo are **unaccented** Vietnamese
  (`"Khong tim thay mau gui len."`). Match that. `recovery_action` must be one of
  `rescan | move_closer | reduce_glare | scan_wider | manual_select | type_query | try_again`
  (`app/schemas/errors.py:10`).
- Never put a client-supplied string into a filesystem path.
- `db_session()` commits on success, rolls back on exception
  (`app/storage/database.py:141`). `promote_submission` takes an open
  connection; it must never open its own.

---

## File Structure

| File | Responsibility |
|---|---|
| `apps/api/app/services/vision_tools_path.py` (new) | Single place that puts `apps/vision-tools` on `sys.path` |
| `apps/api/app/services/promotion_service.py` (new) | Validate reviewed labels; write 4 tables; copy the image |
| `apps/api/app/services/review_service.py` (modify) | Decide accept/edit/reject; call promotion inside one transaction |
| `apps/api/app/services/submission_service.py` (modify) | Add `list_submissions` + `get_submission` reads |
| `apps/api/app/api/deps.py` (new) | `require_admin_token` FastAPI dependency |
| `apps/api/app/api/admin_submissions.py` (modify) | Token-guarded router; two GETs; map errors to status codes |
| `apps/api/app/services/logo_anchor_service.py` (modify) | Use the shared path helper instead of its own `sys.path` block |
| `apps/api/openapi.yaml` (modify) | Two new endpoints, the security scheme, and fix the `POST /api/submissions` body |
| `label_web/boxes.js` (new) | Pure box maths + canvas drawing, shared by both pages |
| `label_web/review.html`, `label_web/review.js` (new) | The review page |
| `label_web/app.js`, `label_web/index.html` (modify) | Consume `boxes.js` rather than keeping private copies |

---

## Task 1: Shared vision-tools path helper

`logo_anchor_service.py:17-20` mutates `sys.path` so `scripts.*` imports work.
`promotion_service` needs `scripts.logo_anchor` too. One helper, not two copies.

**Files:**
- Create: `apps/api/app/services/vision_tools_path.py`
- Modify: `apps/api/app/services/logo_anchor_service.py:17-20`
- Test: `apps/api/tests/test_vision_tools_path.py`

**Interfaces:**
- Produces: `ensure_vision_tools_on_path() -> None`, idempotent.

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_vision_tools_path.py
from __future__ import annotations

import sys

from app.services.vision_tools_path import ensure_vision_tools_on_path
from app.storage.database import ROOT


def test_it_puts_vision_tools_on_sys_path():
    ensure_vision_tools_on_path()
    assert str(ROOT / "apps" / "vision-tools") in sys.path


def test_calling_it_twice_does_not_add_a_second_entry():
    ensure_vision_tools_on_path()
    ensure_vision_tools_on_path()
    entry = str(ROOT / "apps" / "vision-tools")
    assert sys.path.count(entry) == 1


def test_compute_button_offsets_becomes_importable():
    ensure_vision_tools_on_path()
    from scripts.logo_anchor import compute_button_offsets

    offsets = compute_button_offsets(
        {"x": 0, "y": 0, "width": 10, "height": 10},
        {"a": {"x": 10, "y": 0, "width": 5, "height": 5}},
    )
    assert offsets["a"]["dx"] == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk proxy env PYTHONPATH=apps/api pytest -q apps/api/tests/test_vision_tools_path.py`
Expected: FAIL, `ModuleNotFoundError: No module named 'app.services.vision_tools_path'`

- [ ] **Step 3: Write the helper**

```python
# apps/api/app/services/vision_tools_path.py
from __future__ import annotations

import sys

from app.storage.database import ROOT

# vision-tools runs via path, not install (see CLAUDE.md); make its scripts importable.
_VISION_TOOLS = ROOT / "apps" / "vision-tools"


def ensure_vision_tools_on_path() -> None:
    entry = str(_VISION_TOOLS)
    if entry not in sys.path:
        sys.path.insert(0, entry)
```

- [ ] **Step 4: Point `logo_anchor_service` at it**

In `apps/api/app/services/logo_anchor_service.py`, replace lines 17-20:

```python
# vision-tools runs via path, not install (see CLAUDE.md); make its scripts importable.
_VISION_TOOLS = ROOT / "apps" / "vision-tools"
if str(_VISION_TOOLS) not in sys.path:
    sys.path.insert(0, str(_VISION_TOOLS))
```

with:

```python
ensure_vision_tools_on_path()
```

Add `from app.services.vision_tools_path import ensure_vision_tools_on_path` to
the imports (beside `from app.services.template_repository import ...`), and
delete the now-unused `import sys` on line 3.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `rtk proxy env PYTHONPATH=apps/api pytest -q apps/api/tests/test_vision_tools_path.py apps/api/tests/test_boundary_cases.py`
Expected: PASS. `test_boundary_cases.py` imports `logo_anchor_service`; it proves the refactor did not break the import.

- [ ] **Step 6: Lint and commit**

```bash
rtk proxy ruff check apps/api
rtk proxy git add apps/api/app/services/vision_tools_path.py apps/api/app/services/logo_anchor_service.py apps/api/tests/test_vision_tools_path.py
rtk proxy git commit -m "refactor(api): extract the vision-tools sys.path shim"
```

---

## Task 2: Promotion service — validation

Validation first, on its own, because every rejection here is a bug that would
otherwise surface far away: a null `logo_bbox` becomes a 409 at camera time, a
zero-width logo becomes a `ZeroDivisionError` inside `compute_button_offsets`.

**Files:**
- Create: `apps/api/app/services/promotion_service.py`
- Test: `apps/api/tests/test_promotion_validation.py`

**Interfaces:**
- Consumes: `ensure_vision_tools_on_path()` from Task 1.
- Produces:
  - `class PromotionError(ValueError)`
  - `validate_labels(labels: dict[str, Any]) -> None` — raises `PromotionError`
  - `TEMPLATES_DIR: Path`, `SUBMISSIONS_DIR: Path` — module constants, monkeypatchable

- [ ] **Step 1: Write the failing tests**

```python
# apps/api/tests/test_promotion_validation.py
from __future__ import annotations

import pytest

from app.services.promotion_service import PromotionError, validate_labels


def _labels(**overrides):
    labels = {
        "device": {
            "brand": "Panasonic",
            "appliance_type": "microwave",
            "model_name": "NN-GT35HM",
            "display_name": "Lo vi song Panasonic",
        },
        "template": {
            "template_code": "panasonic_microwave_nn_gt35hm_v1",
            "template_image_url": "data/submissions/abc.jpg",
            "logo_bbox": {"x": 476, "y": 3862, "width": 857, "height": 226},
            "panel_bbox": {"x": 238, "y": 428, "width": 5301, "height": 3701},
        },
        "buttons": [
            {
                "button_id": "1",
                "label": "Start",
                "vietnamese_name": "khoi dong",
                "function_description": "bat dau",
                "bbox_template_coordinates": {"x": 10, "y": 10, "width": 50, "height": 50},
                "button_type": "physical",
            }
        ],
    }
    labels.update(overrides)
    return labels


def test_a_complete_submission_validates():
    validate_labels(_labels())


def test_a_missing_logo_bbox_is_rejected():
    template = dict(_labels()["template"], logo_bbox=None)
    with pytest.raises(PromotionError, match="logo_bbox"):
        validate_labels(_labels(template=template))


def test_a_zero_width_logo_is_rejected():
    # compute_button_offsets divides by the logo width.
    template = dict(_labels()["template"], logo_bbox={"x": 0, "y": 0, "width": 0, "height": 10})
    with pytest.raises(PromotionError, match="logo_bbox"):
        validate_labels(_labels(template=template))


def test_a_submission_without_buttons_is_rejected():
    with pytest.raises(PromotionError, match="no buttons"):
        validate_labels(_labels(buttons=[]))


def test_duplicate_button_ids_are_rejected():
    button = _labels()["buttons"][0]
    with pytest.raises(PromotionError, match="duplicate"):
        validate_labels(_labels(buttons=[button, dict(button)]))


def test_a_button_drawn_without_a_name_is_rejected():
    # Matches seed.is_labeled_button: the name is what TTS reads aloud.
    button = dict(_labels()["buttons"][0], vietnamese_name="  ")
    with pytest.raises(PromotionError, match="name"):
        validate_labels(_labels(buttons=[button]))


def test_a_degenerate_button_bbox_is_rejected():
    button = dict(
        _labels()["buttons"][0],
        bbox_template_coordinates={"x": 10, "y": 10, "width": 0, "height": 50},
    )
    with pytest.raises(PromotionError, match="bbox"):
        validate_labels(_labels(buttons=[button]))


def test_an_unknown_button_type_is_rejected():
    # buttons.button_type has a CHECK constraint; a bad value fails the insert.
    button = dict(_labels()["buttons"][0], button_type="slider")
    with pytest.raises(PromotionError, match="button_type"):
        validate_labels(_labels(buttons=[button]))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `rtk proxy env PYTHONPATH=apps/api pytest -q apps/api/tests/test_promotion_validation.py`
Expected: FAIL, `ModuleNotFoundError: No module named 'app.services.promotion_service'`

- [ ] **Step 3: Write the module skeleton and validation**

Import only what this task uses. `ruff` fails the commit on an unused import,
so Tasks 3 and 4 add theirs when they need them.

```python
# apps/api/app/services/promotion_service.py
from __future__ import annotations

from typing import Any

from app.models.common import BUTTON_TYPES
from app.storage.database import ROOT
from app.storage.seed import is_labeled_button

SUBMISSIONS_DIR = ROOT / "data" / "submissions"
TEMPLATES_DIR = ROOT / "data" / "templates"

# Mirrors submissions.py:15. The suffix of the file already on disk decides the
# copy's extension; nothing from the request names a path.
_ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


class PromotionError(ValueError):
    """Reviewed labels cannot become a template."""


def _positive_box(bbox: Any) -> bool:
    if not isinstance(bbox, dict):
        return False
    return float(bbox.get("width", 0)) > 0 and float(bbox.get("height", 0)) > 0


def validate_labels(labels: dict[str, Any]) -> None:
    """Refuse anything that would break detection later. Never repair."""
    template = labels.get("template") or {}
    buttons = labels.get("buttons") or []

    if not _positive_box(template.get("logo_bbox")):
        raise PromotionError("logo_bbox is missing or has no positive size")
    if not buttons:
        raise PromotionError("the submission has no buttons")

    seen: set[str] = set()
    for button in buttons:
        if not is_labeled_button(button):
            raise PromotionError(f"button {button.get('button_id')!r} has no name")
        button_id = button["button_id"]
        if button_id in seen:
            raise PromotionError(f"duplicate button_id: {button_id}")
        seen.add(button_id)
        if not _positive_box(button.get("bbox_template_coordinates")):
            raise PromotionError(f"button {button_id} has a degenerate bbox")
        if button.get("button_type") not in BUTTON_TYPES:
            raise PromotionError(f"button {button_id} has an unknown button_type")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `rtk proxy env PYTHONPATH=apps/api pytest -q apps/api/tests/test_promotion_validation.py`
Expected: PASS, 8 passed

- [ ] **Step 5: Commit**

```bash
rtk proxy ruff check apps/api
rtk proxy git add apps/api/app/services/promotion_service.py apps/api/tests/test_promotion_validation.py
rtk proxy git commit -m "feat(api): validate reviewed labels before promotion"
```

---

## Task 3: Promotion service — image copy

The copy is where a path traversal would live, so it gets its own tests.
Two client-controlled strings reach this code: `template_image_url` (from
`SubmissionCreate`) and, in an earlier draft of the design, `template_code`.
Neither may appear in a path.

**Files:**
- Modify: `apps/api/app/services/promotion_service.py`
- Test: `apps/api/tests/test_promotion_image_copy.py`

**Interfaces:**
- Produces: `copy_submission_image(image_url: str, template_id: str) -> str`
  returning a repo-relative url like `data/templates/template_ab12cd34.png`.

- [ ] **Step 1: Write the failing tests**

```python
# apps/api/tests/test_promotion_image_copy.py
from __future__ import annotations

from pathlib import Path

import pytest

from app.services import promotion_service
from app.services.promotion_service import PromotionError, copy_submission_image


@pytest.fixture()
def dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    submissions = tmp_path / "data" / "submissions"
    templates = tmp_path / "data" / "templates"
    submissions.mkdir(parents=True)
    templates.mkdir(parents=True)
    monkeypatch.setattr(promotion_service, "ROOT", tmp_path)
    monkeypatch.setattr(promotion_service, "SUBMISSIONS_DIR", submissions)
    monkeypatch.setattr(promotion_service, "TEMPLATES_DIR", templates)
    return submissions, templates


def test_it_copies_the_photo_and_returns_the_new_url(dirs):
    submissions, templates = dirs
    (submissions / "abc.png").write_bytes(b"fake-png")

    url = copy_submission_image("data/submissions/abc.png", "template_ab12cd34")

    assert url == "data/templates/template_ab12cd34.png"
    assert (templates / "template_ab12cd34.png").read_bytes() == b"fake-png"


def test_the_original_survives(dirs):
    submissions, _ = dirs
    (submissions / "abc.png").write_bytes(b"fake-png")
    copy_submission_image("data/submissions/abc.png", "template_ab12cd34")
    assert (submissions / "abc.png").is_file()


def test_a_path_outside_the_submissions_directory_is_rejected(dirs):
    # image_url arrives from the client in SubmissionCreate.
    with pytest.raises(PromotionError, match="data/submissions"):
        copy_submission_image("data/templates/panasonic.png", "template_ab12cd34")


def test_a_traversing_image_url_is_rejected(dirs):
    with pytest.raises(PromotionError, match="data/submissions"):
        copy_submission_image("data/submissions/../../etc/passwd", "template_ab12cd34")


def test_a_missing_file_is_rejected(dirs):
    with pytest.raises(PromotionError, match="missing"):
        copy_submission_image("data/submissions/gone.png", "template_ab12cd34")


def test_an_unsupported_suffix_is_rejected(dirs):
    submissions, _ = dirs
    (submissions / "abc.svg").write_bytes(b"<svg/>")
    with pytest.raises(PromotionError, match="image type"):
        copy_submission_image("data/submissions/abc.svg", "template_ab12cd34")


def test_the_destination_name_comes_only_from_the_template_id(dirs):
    submissions, templates = dirs
    (submissions / "abc.jpeg").write_bytes(b"x")
    url = copy_submission_image("data/submissions/abc.jpeg", "template_ab12cd34")
    assert url == "data/templates/template_ab12cd34.jpeg"
    assert [p.name for p in templates.iterdir()] == ["template_ab12cd34.jpeg"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `rtk proxy env PYTHONPATH=apps/api pytest -q apps/api/tests/test_promotion_image_copy.py`
Expected: FAIL, `ImportError: cannot import name 'copy_submission_image'`

- [ ] **Step 3: Implement the copy**

Add `import shutil` to the top of `apps/api/app/services/promotion_service.py`,
then append:

```python
def copy_submission_image(image_url: str, template_id: str) -> str:
    """Copy the submitted photo into data/templates/ and return its new url.

    data/submissions/ is a queue: deleting it must not kill a live template.
    The destination name is built from template_id, which the server minted.
    No part of the request reaches the filesystem path.
    """
    source = (ROOT / image_url).resolve()
    submissions_dir = SUBMISSIONS_DIR.resolve()
    if source.parent != submissions_dir:
        raise PromotionError("the submission image must live in data/submissions/")

    suffix = source.suffix.lower()
    if suffix not in _ALLOWED_IMAGE_SUFFIXES:
        raise PromotionError(f"unsupported image type: {suffix or '(none)'}")
    if not source.is_file():
        raise PromotionError(f"the submission image is missing: {image_url}")

    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    destination = TEMPLATES_DIR / f"{template_id}{suffix}"
    shutil.copyfile(source, destination)
    return f"data/templates/{destination.name}"
```

Note the order: the directory check runs before `is_file()`, so a traversing
path is refused as a traversal rather than as a missing file.

- [ ] **Step 4: Run tests to verify they pass**

Run: `rtk proxy env PYTHONPATH=apps/api pytest -q apps/api/tests/test_promotion_image_copy.py`
Expected: PASS, 7 passed

- [ ] **Step 5: Commit**

```bash
rtk proxy ruff check apps/api
rtk proxy git add apps/api/app/services/promotion_service.py apps/api/tests/test_promotion_image_copy.py
rtk proxy git commit -m "feat(api): copy a submitted photo into data/templates"
```

---

## Task 4: Promotion service — write the four tables

**Files:**
- Modify: `apps/api/app/services/promotion_service.py`
- Test: `apps/api/tests/test_promotion.py`

**Interfaces:**
- Consumes: `validate_labels`, `copy_submission_image`, `compute_button_offsets`.
- Produces: `promote_submission(conn: sqlite3.Connection, submission_id: str, labels: dict[str, Any]) -> str`
  returning the new `template_id`. The caller owns the transaction.

- [ ] **Step 1: Write the failing tests**

```python
# apps/api/tests/test_promotion.py
from __future__ import annotations

from pathlib import Path

import pytest

from app.services import promotion_service
from app.services.promotion_service import PromotionError, promote_submission

SUBMISSION_ID = "ab12cd34-0000-0000-0000-000000000000"


def _labels():
    return {
        "device": {
            "brand": "Panasonic",
            "appliance_type": "microwave",
            "model_name": "NN-GT35HM",
            "display_name": "Lo vi song Panasonic",
            "status": "submitted",  # the wizard sends this; devices CHECK forbids it
        },
        "template": {
            "id": "template_from_the_client",  # must be ignored
            "template_code": "panasonic_microwave_nn_gt35hm_v1",
            "template_image_url": "data/submissions/abc.png",
            "logo_bbox": {"x": 0, "y": 0, "width": 100, "height": 40},
            "panel_bbox": {"x": 0, "y": 0, "width": 800, "height": 600},
            "status": "submitted",
        },
        "buttons": [
            {
                "button_id": "1",
                "label": "Start",
                "vietnamese_name": "khoi dong",
                "function_description": "bat dau",
                "bbox_template_coordinates": {"x": 200, "y": 100, "width": 50, "height": 50},
                "button_type": "physical",
            },
            {
                "button_id": "2",
                "label": "Stop",
                "vietnamese_name": "dung",
                "function_description": "dung lai",
                "bbox_template_coordinates": {"x": 300, "y": 100, "width": 50, "height": 50},
                "button_type": "touch",
            },
        ],
    }


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SILVERTECH_DB_PATH", str(tmp_path / "promo.sqlite3"))
    from app.storage.database import connect, initialize_database

    initialize_database()

    submissions = tmp_path / "data" / "submissions"
    templates = tmp_path / "data" / "templates"
    submissions.mkdir(parents=True)
    templates.mkdir(parents=True)
    (submissions / "abc.png").write_bytes(b"fake-png")
    monkeypatch.setattr(promotion_service, "ROOT", tmp_path)
    monkeypatch.setattr(promotion_service, "SUBMISSIONS_DIR", submissions)
    monkeypatch.setattr(promotion_service, "TEMPLATES_DIR", templates)

    connection = connect()
    yield connection
    connection.close()


def test_it_returns_a_template_id_derived_from_the_submission(conn):
    assert promote_submission(conn, SUBMISSION_ID, _labels()) == "template_ab12cd34"


def test_the_client_supplied_template_id_is_ignored(conn):
    promote_submission(conn, SUBMISSION_ID, _labels())
    ids = [r["id"] for r in conn.execute("SELECT id FROM templates")]
    assert ids == ["template_ab12cd34"]


def test_the_device_is_active_and_the_template_is_official(conn):
    # list_candidates filters on exactly these two columns; get either wrong and
    # the promoted template is invisible to the camera.
    promote_submission(conn, SUBMISSION_ID, _labels())
    assert conn.execute("SELECT status FROM devices").fetchone()["status"] == "active"
    assert conn.execute("SELECT status FROM templates").fetchone()["status"] == "official"


def test_it_writes_every_button(conn):
    promote_submission(conn, SUBMISSION_ID, _labels())
    rows = conn.execute("SELECT id, button_id FROM buttons ORDER BY button_id").fetchall()
    assert [r["button_id"] for r in rows] == ["1", "2"]
    assert [r["id"] for r in rows] == ["btn_ab12cd34_1", "btn_ab12cd34_2"]


def test_it_writes_button_offsets(conn):
    # The whole feature turns on this table. run_logo_anchor raises 409
    # "no button_offsets" without it.
    from scripts.logo_anchor import compute_button_offsets

    promote_submission(conn, SUBMISSION_ID, _labels())
    labels = _labels()
    expected = compute_button_offsets(
        labels["template"]["logo_bbox"],
        {b["button_id"]: b["bbox_template_coordinates"] for b in labels["buttons"]},
    )
    rows = conn.execute("SELECT button_id, dx, dy, dw, dh FROM button_offsets").fetchall()
    actual = {r["button_id"]: {"dx": r["dx"], "dy": r["dy"], "dw": r["dw"], "dh": r["dh"]} for r in rows}
    assert actual == expected


def test_the_template_points_at_the_copied_image(conn):
    promote_submission(conn, SUBMISSION_ID, _labels())
    row = conn.execute("SELECT template_image_url, template_code FROM templates").fetchone()
    assert row["template_image_url"] == "data/templates/template_ab12cd34.png"
    assert row["template_code"] == "panasonic_microwave_nn_gt35hm_v1"


def test_invalid_labels_write_nothing(conn):
    labels = _labels()
    labels["template"]["logo_bbox"] = None
    with pytest.raises(PromotionError):
        promote_submission(conn, SUBMISSION_ID, labels)
    assert conn.execute("SELECT count(*) AS n FROM devices").fetchone()["n"] == 0


def test_a_missing_photo_writes_nothing(conn):
    labels = _labels()
    labels["template"]["template_image_url"] = "data/submissions/gone.png"
    with pytest.raises(PromotionError):
        promote_submission(conn, SUBMISSION_ID, labels)
    assert conn.execute("SELECT count(*) AS n FROM templates").fetchone()["n"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `rtk proxy env PYTHONPATH=apps/api pytest -q apps/api/tests/test_promotion.py`
Expected: FAIL, `ImportError: cannot import name 'promote_submission'`

- [ ] **Step 3: Implement promotion**

Extend the imports of `apps/api/app/services/promotion_service.py`. The
`scripts.logo_anchor` import must sit **after** the `ensure_vision_tools_on_path()`
call, which is why it carries a `noqa`:

```python
import sqlite3
import time

from app.models.common import BUTTON_TYPES, encode_json
from app.services.vision_tools_path import ensure_vision_tools_on_path

ensure_vision_tools_on_path()

from scripts.logo_anchor import compute_button_offsets  # noqa: E402
```

Then append:

```python
def _short_id(submission_id: str) -> str:
    """Eight hex characters of the submission uuid.

    Two submissions could share a prefix. They would collide on a primary key
    inside the caller's transaction, roll it back, and write nothing.
    """
    return submission_id.replace("-", "")[:8]


def promote_submission(
    conn: sqlite3.Connection,
    submission_id: str,
    labels: dict[str, Any],
) -> str:
    """Insert devices/templates/buttons/button_offsets from reviewed labels.

    Returns the new template_id. The caller owns the transaction: a failed copy
    or a bad bbox must not leave an orphan devices row behind.
    """
    validate_labels(labels)

    sid = _short_id(submission_id)
    device_id = f"device_{sid}"
    template_id = f"template_{sid}"
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    device = labels["device"]
    template = labels["template"]
    buttons = labels["buttons"]
    logo_bbox = template["logo_bbox"]

    image_url = copy_submission_image(template["template_image_url"], template_id)

    # Statuses are the server's to set. The wizard sends 'submitted' for the
    # device, which devices' CHECK (status IN ('active','archived')) forbids.
    conn.execute(
        """
        INSERT INTO devices
        (id, brand, appliance_type, model_name, display_name, status, created_at, updated_at)
        VALUES (:id, :brand, :appliance_type, :model_name, :display_name, 'active', :now, :now)
        """,
        {
            "id": device_id,
            "brand": device["brand"],
            "appliance_type": device["appliance_type"],
            "model_name": device.get("model_name"),
            "display_name": device["display_name"],
            "now": now,
        },
    )
    conn.execute(
        """
        INSERT INTO templates
        (id, device_id, template_code, template_image_url, logo_bbox, panel_bbox,
         feature_descriptor_path, version, status, created_at, updated_at)
        VALUES (:id, :device_id, :template_code, :template_image_url, :logo_bbox, :panel_bbox,
                NULL, 1, 'official', :now, :now)
        """,
        {
            "id": template_id,
            "device_id": device_id,
            "template_code": template["template_code"],
            "template_image_url": image_url,
            "logo_bbox": encode_json(logo_bbox),
            "panel_bbox": encode_json(template["panel_bbox"]) if template.get("panel_bbox") else None,
            "now": now,
        },
    )
    for button in buttons:
        conn.execute(
            """
            INSERT INTO buttons
            (id, template_id, button_id, label, vietnamese_name, function_description,
             bbox_template_coordinates, polygon_template_coordinates, button_type,
             created_at, updated_at)
            VALUES (:id, :template_id, :button_id, :label, :vietnamese_name, :function_description,
                    :bbox, :polygon, :button_type, :now, :now)
            """,
            {
                "id": f"btn_{sid}_{button['button_id']}",
                "template_id": template_id,
                "button_id": button["button_id"],
                "label": button["label"],
                "vietnamese_name": button["vietnamese_name"],
                "function_description": button["function_description"],
                "bbox": encode_json(button["bbox_template_coordinates"]),
                "polygon": encode_json(button["polygon_template_coordinates"])
                if button.get("polygon_template_coordinates")
                else None,
                "button_type": button["button_type"],
                "now": now,
            },
        )

    # Without these rows run_logo_anchor raises 409 and the template is inert.
    offsets = compute_button_offsets(
        logo_bbox,
        {b["button_id"]: b["bbox_template_coordinates"] for b in buttons},
    )
    for button_id, offset in offsets.items():
        conn.execute(
            """
            INSERT INTO button_offsets (template_id, button_id, dx, dy, dw, dh, updated_at)
            VALUES (:template_id, :button_id, :dx, :dy, :dw, :dh, :now)
            """,
            {"template_id": template_id, "button_id": button_id, **offset, "now": now},
        )
    return template_id
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `rtk proxy env PYTHONPATH=apps/api pytest -q apps/api/tests/test_promotion.py`
Expected: PASS, 8 passed

- [ ] **Step 5: Commit**

```bash
rtk proxy ruff check apps/api
rtk proxy git add apps/api/app/services/promotion_service.py apps/api/tests/test_promotion.py
rtk proxy git commit -m "feat(api): promote a reviewed submission into a template"
```

---

## Task 5: Review service wiring

**Files:**
- Modify: `apps/api/app/services/review_service.py` (whole file)
- Modify: `apps/api/app/api/admin_submissions.py:13-19`
- Test: `apps/api/tests/test_review_service.py`

**Interfaces:**
- Consumes: `promote_submission`, `PromotionError`.
- Produces:
  - `class AlreadyReviewedError(Exception)`
  - `review_submission(submission_id, decision, reviewer_note, edited_template=None) -> dict`
    returning `{"submission_id": str, "status": str, "template_id": str | None}`

- [ ] **Step 1: Write the failing tests**

```python
# apps/api/tests/test_review_service.py
from __future__ import annotations

from pathlib import Path

import pytest

from app.services import promotion_service
from app.services.promotion_service import PromotionError
from app.services.review_service import AlreadyReviewedError, review_submission
from app.services.submission_service import create_submission

LABELS = {
    "device": {
        "brand": "Panasonic",
        "appliance_type": "microwave",
        "model_name": "NN-GT35HM",
        "display_name": "Lo vi song Panasonic",
    },
    "template": {
        "template_code": "panasonic_microwave_nn_gt35hm_v1",
        "template_image_url": "data/submissions/abc.png",
        "logo_bbox": {"x": 0, "y": 0, "width": 100, "height": 40},
        "panel_bbox": None,
    },
    "buttons": [
        {
            "button_id": "1",
            "label": "Start",
            "vietnamese_name": "khoi dong",
            "function_description": "bat dau",
            "bbox_template_coordinates": {"x": 200, "y": 100, "width": 50, "height": 50},
            "button_type": "physical",
        }
    ],
}


@pytest.fixture()
def submission_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SILVERTECH_DB_PATH", str(tmp_path / "review.sqlite3"))
    from app.storage.database import initialize_database

    initialize_database()

    submissions = tmp_path / "data" / "submissions"
    templates = tmp_path / "data" / "templates"
    submissions.mkdir(parents=True)
    templates.mkdir(parents=True)
    (submissions / "abc.png").write_bytes(b"fake-png")
    monkeypatch.setattr(promotion_service, "ROOT", tmp_path)
    monkeypatch.setattr(promotion_service, "SUBMISSIONS_DIR", submissions)
    monkeypatch.setattr(promotion_service, "TEMPLATES_DIR", templates)

    return create_submission(
        {
            "submitted_by": None,
            "brand": "Panasonic",
            "appliance_type": "microwave",
            "image_url": "data/submissions/abc.png",
            "proposed_labels_json": LABELS,
        }
    )


def _count(table: str) -> int:
    from app.storage.database import db_session

    with db_session() as conn:
        return conn.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"]


def test_accept_promotes_and_returns_the_template_id(submission_id):
    result = review_submission(submission_id, "accept", None)
    assert result["status"] == "accepted"
    assert result["template_id"].startswith("template_")
    assert _count("templates") == 1


def test_reject_creates_no_template(submission_id):
    result = review_submission(submission_id, "reject", "anh mo")
    assert result == {"submission_id": submission_id, "status": "rejected", "template_id": None}
    assert _count("templates") == 0


def test_edit_promotes_the_edited_labels(submission_id):
    edited = {**LABELS, "buttons": [dict(LABELS["buttons"][0], vietnamese_name="bat dau ngay")]}
    review_submission(submission_id, "edit", None, edited_template=edited)

    from app.storage.database import db_session

    with db_session() as conn:
        name = conn.execute("SELECT vietnamese_name FROM buttons").fetchone()["vietnamese_name"]
    assert name == "bat dau ngay"


def test_edit_without_edited_template_is_refused(submission_id):
    with pytest.raises(PromotionError, match="edited_template"):
        review_submission(submission_id, "edit", None)
    assert _count("templates") == 0


def test_reviewing_twice_is_refused_and_changes_nothing(submission_id):
    review_submission(submission_id, "accept", None)
    with pytest.raises(AlreadyReviewedError):
        review_submission(submission_id, "accept", None)
    assert _count("templates") == 1
    assert _count("devices") == 1


def test_an_unknown_submission_raises_key_error(submission_id):
    with pytest.raises(KeyError):
        review_submission("no-such-id", "accept", None)


def test_a_bad_decision_raises_value_error(submission_id):
    with pytest.raises(ValueError):
        review_submission(submission_id, "maybe", None)


def test_a_failed_promotion_leaves_the_submission_pending(submission_id):
    # Rollback must cover the status update too, or a retry is impossible.
    from app.storage.database import db_session

    with db_session() as conn:
        conn.execute("UPDATE submissions SET proposed_labels_json = '{}' WHERE id = :id",
                     {"id": submission_id})
    with pytest.raises(PromotionError):
        review_submission(submission_id, "accept", None)
    with db_session() as conn:
        status = conn.execute("SELECT status FROM submissions WHERE id = :id",
                              {"id": submission_id}).fetchone()["status"]
    assert status == "pending"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `rtk proxy env PYTHONPATH=apps/api pytest -q apps/api/tests/test_review_service.py`
Expected: FAIL, `ImportError: cannot import name 'AlreadyReviewedError'`

- [ ] **Step 3: Rewrite `review_service.py`**

```python
# apps/api/app/services/review_service.py
from __future__ import annotations

from typing import Any

from app.models.common import decode_json
from app.services.promotion_service import PromotionError, promote_submission
from app.storage.database import db_session

_DECISIONS = {"accept", "edit", "reject"}


class AlreadyReviewedError(Exception):
    """The submission has already been accepted or rejected."""


def review_submission(
    submission_id: str,
    decision: str,
    reviewer_note: str | None,
    edited_template: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if decision not in _DECISIONS:
        raise ValueError("decision must be accept, edit, or reject")
    if decision == "edit" and not edited_template:
        raise PromotionError("edit requires edited_template")

    with db_session() as conn:
        row = conn.execute(
            "SELECT status, proposed_labels_json FROM submissions WHERE id = :id",
            {"id": submission_id},
        ).fetchone()
        if row is None:
            raise KeyError(submission_id)
        if row["status"] != "pending":
            raise AlreadyReviewedError(submission_id)

        template_id: str | None = None
        if decision == "reject":
            status = "rejected"
        else:
            status = "accepted"
            labels = (
                edited_template
                if decision == "edit"
                else decode_json(row["proposed_labels_json"], default={})
            )
            # Raises inside the session, so the UPDATE below never lands.
            template_id = promote_submission(conn, submission_id, labels)

        conn.execute(
            "UPDATE submissions SET status = :status, reviewer_note = :note WHERE id = :id",
            {"status": status, "note": reviewer_note, "id": submission_id},
        )
    return {"submission_id": submission_id, "status": status, "template_id": template_id}
```

- [ ] **Step 4: Map the new errors in the router**

Replace `apps/api/app/api/admin_submissions.py` lines 1-19 with:

```python
from __future__ import annotations

from fastapi import APIRouter

from app.schemas.errors import friendly_error
from app.schemas.templates import SubmissionReview
from app.services.promotion_service import PromotionError
from app.services.review_service import AlreadyReviewedError, review_submission

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/submissions/{submission_id}/review")
def review(submission_id: str, payload: SubmissionReview) -> dict:
    try:
        return review_submission(
            submission_id,
            payload.decision,
            payload.reviewer_note,
            payload.edited_template,
        )
    except KeyError as exc:
        raise friendly_error(404, "Khong tim thay mau gui len.", "try_again") from exc
    except AlreadyReviewedError as exc:
        raise friendly_error(409, "Mau gui len da duoc duyet roi.", "try_again") from exc
    except PromotionError as exc:
        raise friendly_error(400, "Nhan cua mau gui len chua dung.", "try_again") from exc
    except ValueError as exc:
        raise friendly_error(400, "Quyet dinh duyet khong hop le.", "try_again") from exc
```

`PromotionError` subclasses `ValueError`, so it must be caught before it.
`AlreadyReviewedError` does not, but keep it first for symmetry.

- [ ] **Step 5: Run tests to verify they pass**

Run: `rtk proxy env PYTHONPATH=apps/api pytest -q apps/api/tests/test_review_service.py`
Expected: PASS, 8 passed

- [ ] **Step 6: Commit**

```bash
rtk proxy ruff check apps/api
rtk proxy git add apps/api/app/services/review_service.py apps/api/app/api/admin_submissions.py apps/api/tests/test_review_service.py
rtk proxy git commit -m "feat(api): accepting a submission now creates a template"
```

---

## Task 6: Prove a promoted template is detectable

The one test that shows this feature does anything. Everything up to here could
pass while `run_logo_anchor` still refuses the template.

**Files:**
- Test: `apps/api/tests/test_promoted_template_is_detectable.py`

**Interfaces:**
- Consumes: `review_submission`, `create_submission`, `run_logo_anchor`, `list_candidates`.

- [ ] **Step 1: Write the test**

```python
# apps/api/tests/test_promoted_template_is_detectable.py
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

cv2 = pytest.importorskip("cv2")

REAL_ROOT = Path(__file__).resolve().parents[3]
PANEL = REAL_ROOT / "data" / "templates" / "panasonic_microwave_nn_gt35hm.png"
LABELS = REAL_ROOT / "data" / "templates" / "labels" / "panasonic_microwave_nn_gt35hm_v1.json"


@pytest.fixture()
def promoted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SILVERTECH_DB_PATH", str(tmp_path / "detect.sqlite3"))
    from app.services import promotion_service
    from app.services.review_service import review_submission
    from app.services.submission_service import create_submission
    from app.storage.database import initialize_database

    initialize_database()  # empty DB: no seeded template shares this photo

    submissions = tmp_path / "data" / "submissions"
    templates = tmp_path / "data" / "templates"
    submissions.mkdir(parents=True)
    templates.mkdir(parents=True)
    shutil.copyfile(PANEL, submissions / "panel.png")
    monkeypatch.setattr(promotion_service, "ROOT", tmp_path)
    monkeypatch.setattr(promotion_service, "SUBMISSIONS_DIR", submissions)
    monkeypatch.setattr(promotion_service, "TEMPLATES_DIR", templates)

    # logo_anchor_service resolves template_image_url against its own ROOT.
    from app.services import logo_anchor_service

    monkeypatch.setattr(logo_anchor_service, "ROOT", tmp_path)

    reviewed = json.loads(LABELS.read_text(encoding="utf-8"))
    labels = {
        "device": reviewed["device"],
        "template": {
            "template_code": "panasonic_microwave_nn_gt35hm_v1",
            "template_image_url": "data/submissions/panel.png",
            "logo_bbox": reviewed["template"]["logo_bbox"],
            "panel_bbox": reviewed["template"]["panel_bbox"],
        },
        "buttons": reviewed["buttons"][:3],
    }
    submission_id = create_submission(
        {
            "submitted_by": None,
            "brand": "Panasonic",
            "appliance_type": "microwave",
            "image_url": "data/submissions/panel.png",
            "proposed_labels_json": labels,
        }
    )
    result = review_submission(submission_id, "accept", None)
    return result["template_id"]


def test_the_promoted_template_is_a_detection_candidate(promoted):
    # Wrong device/template status and list_candidates filters it straight out.
    from app.services.template_repository import list_candidates

    assert promoted in {c["id"] for c in list_candidates(None, None)}


def test_run_logo_anchor_matches_the_promoted_template(promoted):
    # Without button_offsets this raises 409 "no button_offsets; run
    # compute_logo_offsets.py first" -- the omission that made the whole
    # submission flow inert.
    from app.services.logo_anchor_service import run_logo_anchor

    result = run_logo_anchor(promoted, PANEL.read_bytes())

    assert result["template_id"] == promoted
    assert result["accepted"] is True
    assert set(result["projected_buttons"]) == {"micro_power", "time_10_min", "grill"}
```

- [ ] **Step 2: Run it**

Run: `rtk proxy env PYTHONPATH=apps/api:apps/vision-tools pytest -q apps/api/tests/test_promoted_template_is_detectable.py -v`
Expected: PASS, 2 passed. This test decodes a 5712×4284 png and runs SIFT; ten
seconds is normal.

If `projected_buttons` is not the result key, read what `match_with_logo_anchor`
returns in `apps/vision-tools/scripts/logo_anchor_match.py` and use that name.
Do not weaken the assertion to `assert result` — the point is that the buttons
project.

- [ ] **Step 3: Commit**

```bash
rtk proxy git add apps/api/tests/test_promoted_template_is_detectable.py
rtk proxy git commit -m "test(api): a promoted submission is detectable end to end"
```

---

## Task 7: Admin token

`/api/admin` currently writes the `templates` table the runtime serves from, on
a permanent public ngrok domain, with no authentication.

**Files:**
- Create: `apps/api/app/api/deps.py`
- Modify: `apps/api/app/api/admin_submissions.py` (router construction)
- Modify: `apps/api/tests/conftest.py`, `tests/conftest.py`
- Modify: `tests/contract/test_admin_review_contract.py`
- Modify: `.env.example`
- Test: `apps/api/tests/test_admin_token.py`

**Interfaces:**
- Produces: `require_admin_token(x_admin_token: str | None = Header(default=None)) -> None`

- [ ] **Step 1: Write the failing tests**

```python
# apps/api/tests/test_admin_token.py
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SILVERTECH_DB_PATH", str(tmp_path / "auth.sqlite3"))
    from app.storage.seed import seed_database

    seed_database()
    from app.main import app

    return TestClient(app)


def test_without_the_header_the_request_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("SILVERTECH_ADMIN_TOKEN", "s3cret")
    response = _client(tmp_path, monkeypatch).post(
        "/api/admin/submissions/whatever/review", json={"decision": "reject"}
    )
    assert response.status_code == 401


def test_a_wrong_token_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("SILVERTECH_ADMIN_TOKEN", "s3cret")
    response = _client(tmp_path, monkeypatch).post(
        "/api/admin/submissions/whatever/review",
        json={"decision": "reject"},
        headers={"X-Admin-Token": "guess"},
    )
    assert response.status_code == 401


def test_an_unset_token_closes_the_router(tmp_path, monkeypatch):
    # Default closed. Forgetting to configure the server must not be the thing
    # that opens the door.
    monkeypatch.delenv("SILVERTECH_ADMIN_TOKEN", raising=False)
    response = _client(tmp_path, monkeypatch).post(
        "/api/admin/submissions/whatever/review",
        json={"decision": "reject"},
        headers={"X-Admin-Token": "anything"},
    )
    assert response.status_code == 503


def test_the_right_token_reaches_the_handler(tmp_path, monkeypatch):
    monkeypatch.setenv("SILVERTECH_ADMIN_TOKEN", "s3cret")
    response = _client(tmp_path, monkeypatch).post(
        "/api/admin/submissions/whatever/review",
        json={"decision": "reject"},
        headers={"X-Admin-Token": "s3cret"},
    )
    assert response.status_code == 404  # past the guard, submission not found
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `rtk proxy env PYTHONPATH=apps/api pytest -q apps/api/tests/test_admin_token.py`
Expected: FAIL — the first three return 404, not 401/503.

- [ ] **Step 3: Write the dependency**

```python
# apps/api/app/api/deps.py
from __future__ import annotations

import os
import secrets

from fastapi import Header

from app.schemas.errors import friendly_error


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    """Guard /api/admin, which writes the templates table the runtime serves from.

    Default closed: an unset SILVERTECH_ADMIN_TOKEN disables the router rather
    than disabling the check.
    """
    expected = os.getenv("SILVERTECH_ADMIN_TOKEN", "").strip()
    if not expected:
        raise friendly_error(503, "Chuc nang duyet chua duoc bat tren may chu.", "try_again")
    if not x_admin_token or not secrets.compare_digest(x_admin_token, expected):
        raise friendly_error(401, "Khong co quyen duyet.", "try_again")
```

- [ ] **Step 4: Attach it to the router**

In `apps/api/app/api/admin_submissions.py`, change the import block and the
router construction:

```python
from fastapi import APIRouter, Depends

from app.api.deps import require_admin_token

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_token)],
)
```

- [ ] **Step 5: Give the test clients a token**

Add to **both** `apps/api/tests/conftest.py` and `tests/conftest.py`, inside the
`client` fixture, right after the `SILVERTECH_DB_PATH` line:

```python
    monkeypatch.setenv("SILVERTECH_ADMIN_TOKEN", "test-token")
```

Then in `tests/contract/test_admin_review_contract.py`, add the header to the
review call:

```python
    response = client.post(
        f"/api/admin/submissions/{submission['submission_id']}/review",
        json={"decision": "reject", "reviewer_note": "Needs clearer panel image"},
        headers={"X-Admin-Token": "test-token"},
    )
```

- [ ] **Step 6: Document the variable**

In `.env.example`, beside `SILVERTECH_CORS_ORIGINS`:

```
# Required for POST/GET /api/admin/*. Unset means the admin router answers 503.
# Reviewing a submission writes the templates table the app serves from, so this
# must be set to a long random string whenever the API is reachable from outside.
SILVERTECH_ADMIN_TOKEN=
```

- [ ] **Step 7: Run the full API and contract suites**

Run: `rtk proxy env PYTHONPATH=apps/api pytest -q apps/api/tests tests/contract`
Expected: PASS. `test_admin_review_contract` proves the header plumbing works.

- [ ] **Step 8: Commit**

```bash
rtk proxy ruff check apps/api
rtk proxy git add apps/api/app/api/deps.py apps/api/app/api/admin_submissions.py apps/api/tests/test_admin_token.py apps/api/tests/conftest.py tests/conftest.py tests/contract/test_admin_review_contract.py .env.example
rtk proxy git commit -m "feat(api): require X-Admin-Token on /api/admin, default closed"
```

---

## Task 8: Admin read endpoints

**Files:**
- Modify: `apps/api/app/services/submission_service.py`
- Modify: `apps/api/app/api/admin_submissions.py`
- Test: `apps/api/tests/test_admin_submission_reads.py`

**Interfaces:**
- Produces:
  - `list_submissions(status: str | None = None) -> list[dict[str, Any]]`
  - `get_submission(submission_id: str) -> dict[str, Any]` — raises `KeyError`
  - `GET /api/admin/submissions?status=pending`
  - `GET /api/admin/submissions/{submission_id}`

- [ ] **Step 1: Write the failing tests**

```python
# apps/api/tests/test_admin_submission_reads.py
from __future__ import annotations

HEADERS = {"X-Admin-Token": "test-token"}

LABELS = {"device": {}, "template": {}, "buttons": [{"button_id": "1"}]}


def _submit(client, brand="Panasonic"):
    return client.post(
        "/api/submissions",
        json={
            "brand": brand,
            "appliance_type": "microwave",
            "image_url": "data/submissions/abc.png",
            "proposed_labels_json": LABELS,
        },
    ).json()["submission_id"]


def test_listing_requires_the_token(client):
    assert client.get("/api/admin/submissions").status_code == 401


def test_it_lists_pending_submissions(client):
    submission_id = _submit(client)
    rows = client.get("/api/admin/submissions?status=pending", headers=HEADERS).json()
    assert [r["id"] for r in rows] == [submission_id]
    assert rows[0]["brand"] == "Panasonic"
    assert rows[0]["image_url"] == "data/submissions/abc.png"


def test_the_list_is_not_filtered_without_a_status(client):
    _submit(client)
    assert len(client.get("/api/admin/submissions", headers=HEADERS).json()) == 1


def test_a_reviewed_submission_leaves_the_pending_list(client):
    submission_id = _submit(client)
    client.post(
        f"/api/admin/submissions/{submission_id}/review",
        json={"decision": "reject"},
        headers=HEADERS,
    )
    assert client.get("/api/admin/submissions?status=pending", headers=HEADERS).json() == []


def test_the_detail_returns_decoded_labels(client):
    submission_id = _submit(client)
    body = client.get(f"/api/admin/submissions/{submission_id}", headers=HEADERS).json()
    assert body["id"] == submission_id
    assert body["proposed_labels_json"] == LABELS
    assert body["status"] == "pending"


def test_an_unknown_submission_is_a_404(client):
    assert client.get("/api/admin/submissions/nope", headers=HEADERS).status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `rtk proxy env PYTHONPATH=apps/api pytest -q apps/api/tests/test_admin_submission_reads.py`
Expected: FAIL, the GETs return 405 (only POST is registered on that path).

- [ ] **Step 3: Add the reads to `submission_service.py`**

Append:

```python
_SUBMISSION_COLUMNS = "id, submitted_by, brand, appliance_type, image_url, status, reviewer_note, created_at"


def list_submissions(status: str | None = None) -> list[dict[str, Any]]:
    query = f"SELECT {_SUBMISSION_COLUMNS} FROM submissions"
    params: dict[str, Any] = {}
    if status:
        query += " WHERE status = :status"
        params["status"] = status
    query += " ORDER BY created_at DESC"
    with db_session() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def get_submission(submission_id: str) -> dict[str, Any]:
    with db_session() as conn:
        row = conn.execute(
            f"SELECT {_SUBMISSION_COLUMNS}, proposed_labels_json FROM submissions WHERE id = :id",
            {"id": submission_id},
        ).fetchone()
    if row is None:
        raise KeyError(submission_id)
    submission = dict(row)
    submission["proposed_labels_json"] = decode_json(submission["proposed_labels_json"], default={})
    return submission
```

and extend its imports:

```python
from typing import Any

from app.models.common import decode_json, encode_json
```

- [ ] **Step 4: Add the endpoints**

Append to `apps/api/app/api/admin_submissions.py`:

```python
@router.get("/submissions")
def list_pending(status: str | None = None) -> list[dict]:
    return list_submissions(status)


@router.get("/submissions/{submission_id}")
def read_submission(submission_id: str) -> dict:
    try:
        return get_submission(submission_id)
    except KeyError as exc:
        raise friendly_error(404, "Khong tim thay mau gui len.", "try_again") from exc
```

and import them:

```python
from app.services.submission_service import get_submission, list_submissions
```

Register order matters: `/submissions/{submission_id}` must not shadow
`/submissions`. FastAPI matches the literal path first, so declaring the list
route before the detail route keeps it unambiguous.

- [ ] **Step 5: Run tests to verify they pass**

Run: `rtk proxy env PYTHONPATH=apps/api pytest -q apps/api/tests/test_admin_submission_reads.py`
Expected: PASS, 6 passed

- [ ] **Step 6: Commit**

```bash
rtk proxy ruff check apps/api
rtk proxy git add apps/api/app/services/submission_service.py apps/api/app/api/admin_submissions.py apps/api/tests/test_admin_submission_reads.py
rtk proxy git commit -m "feat(api): list and read submissions for review"
```

---

## Task 9: Fix the contract

`openapi.yaml:127` declares `POST /api/submissions` as `multipart/form-data`.
`submissions.py:19` takes JSON and the image goes through a separate
`POST /api/submissions/image`. The contract has been wrong since it was written
and `tests/contract/` stayed green, which means those tests do not check what
they appear to check.

**Files:**
- Modify: `apps/api/openapi.yaml`
- Test: `tests/contract/test_admin_submission_contract.py` (new)

- [ ] **Step 1: Correct `POST /api/submissions`**

Replace the `requestBody` of `/api/submissions` (`openapi.yaml:131-146`) with:

```yaml
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [brand, appliance_type, image_url, proposed_labels_json]
              properties:
                submitted_by:
                  type: string
                  nullable: true
                brand:
                  type: string
                appliance_type:
                  type: string
                image_url:
                  type: string
                  description: Returned by POST /api/submissions/image
                proposed_labels_json:
                  $ref: "#/components/schemas/TemplateEdit"
```

- [ ] **Step 2: Add `POST /api/submissions/image`**

After the `/api/submissions` block:

```yaml
  /api/submissions/image:
    post:
      summary: Upload a panel photo and get back its image_url
      operationId: uploadSubmissionImage
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              required: [image]
              properties:
                image:
                  type: string
                  format: binary
      responses:
        "201":
          description: Stored under data/submissions/
          content:
            application/json:
              schema:
                type: object
                required: [image_url]
                properties:
                  image_url:
                    type: string
        "400":
          $ref: "#/components/responses/FriendlyError"
```

- [ ] **Step 3: Add the two admin reads and the security scheme**

Before `/api/admin/submissions/{id}/review`:

```yaml
  /api/admin/submissions:
    get:
      summary: List submissions, newest first
      operationId: listSubmissions
      security:
        - AdminToken: []
      parameters:
        - name: status
          in: query
          required: false
          schema:
            type: string
            enum: [pending, accepted, rejected]
      responses:
        "200":
          description: Submissions
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: "#/components/schemas/SubmissionSummary"
        "401":
          $ref: "#/components/responses/FriendlyError"
        "503":
          $ref: "#/components/responses/FriendlyError"
  /api/admin/submissions/{id}:
    get:
      summary: One submission with its proposed labels
      operationId: getSubmission
      security:
        - AdminToken: []
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: Submission detail
          content:
            application/json:
              schema:
                allOf:
                  - $ref: "#/components/schemas/SubmissionSummary"
                  - type: object
                    required: [proposed_labels_json]
                    properties:
                      proposed_labels_json:
                        $ref: "#/components/schemas/TemplateEdit"
        "404":
          $ref: "#/components/responses/FriendlyError"
```

Add `security: [{AdminToken: []}]` and a `"409"` response to the existing
`/api/admin/submissions/{id}/review` operation, beside its `"400"`:

```yaml
        "409":
          $ref: "#/components/responses/FriendlyError"
```

Under `components:`, add a sibling of `responses:` and `schemas:`:

```yaml
  securitySchemes:
    AdminToken:
      type: apiKey
      in: header
      name: X-Admin-Token
```

Under `components.schemas:`, add:

```yaml
    SubmissionSummary:
      type: object
      required: [id, brand, appliance_type, image_url, status, created_at]
      properties:
        id:
          type: string
        submitted_by:
          type: string
          nullable: true
        brand:
          type: string
        appliance_type:
          type: string
        image_url:
          type: string
        status:
          type: string
          enum: [pending, accepted, rejected]
        reviewer_note:
          type: string
          nullable: true
        created_at:
          type: string
```

- [ ] **Step 4: Write a contract test that would have caught the drift**

```python
# tests/contract/test_admin_submission_contract.py
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SPEC = yaml.safe_load((ROOT / "apps" / "api" / "openapi.yaml").read_text(encoding="utf-8"))

HEADERS = {"X-Admin-Token": "test-token"}


def test_the_contract_declares_the_submission_body_as_json():
    body = SPEC["paths"]["/api/submissions"]["post"]["requestBody"]["content"]
    assert list(body) == ["application/json"]


def test_the_contract_declares_the_image_upload():
    body = SPEC["paths"]["/api/submissions/image"]["post"]["requestBody"]["content"]
    assert list(body) == ["multipart/form-data"]


def test_every_admin_path_requires_the_token():
    admin = {p: v for p, v in SPEC["paths"].items() if p.startswith("/api/admin")}
    assert admin
    for path, operations in admin.items():
        for method, operation in operations.items():
            assert operation.get("security") == [{"AdminToken": []}], f"{method} {path}"


def test_the_summary_fields_match_what_the_endpoint_returns(client):
    client.post(
        "/api/submissions",
        json={
            "brand": "Panasonic",
            "appliance_type": "microwave",
            "image_url": "data/submissions/abc.png",
            "proposed_labels_json": {"buttons": [{"button_id": "1"}]},
        },
    )
    row = client.get("/api/admin/submissions", headers=HEADERS).json()[0]
    required = SPEC["components"]["schemas"]["SubmissionSummary"]["required"]
    assert set(required) <= set(row)
```

`PyYAML` is already a transitive dependency of the vision tools; if the import
fails, add `pyyaml` to the `dev` extra in `apps/api/pyproject.toml:17`.

- [ ] **Step 5: Run the contract suite**

Run: `rtk proxy env PYTHONPATH=apps/api pytest -q tests/contract`
Expected: PASS, 6 passed

- [ ] **Step 6: Commit**

```bash
rtk proxy git add apps/api/openapi.yaml tests/contract/test_admin_submission_contract.py
rtk proxy git commit -m "docs(api): correct the submission contract and declare the admin reads"
```

---

## Task 10: Extract `boxes.js`

`app.js` is 585 lines of plain script — no modules, globals bound to element ids
in `index.html`. The review page needs the same box maths and the same canvas
drawing. Copying them would leave two drifting drawing routines.

Only the DOM-free helpers move. `draw()`, `refresh()` and everything touching
`state` stay in `app.js`; the review page has different state.

**Files:**
- Create: `label_web/boxes.js`
- Modify: `label_web/app.js` (delete the moved functions, adapt call sites)
- Modify: `label_web/index.html` (load `boxes.js` before `app.js`)

**Interfaces:**
- Produces, as globals (no bundler, no `import`):
  - `slug(value: string) -> string`
  - `nowIso() -> string`
  - `box(x, y, width, height) -> {x, y, width, height}` — rounded, non-negative
  - `screenToImage(evt, canvas, scale) -> {x, y}`
  - `drawBox(ctx, rect, scale, color, label, active) -> void`

- [ ] **Step 1: Create `boxes.js`**

```javascript
// label_web/boxes.js
// Shared by index.html (labelling) and review.html (admin review). Plain script,
// no modules: both pages load it with a <script src> before their own file.

function slug(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function nowIso() {
  return new Date().toISOString();
}

function box(x, y, width, height) {
  const nx = Math.round(Math.min(x, x + width));
  const ny = Math.round(Math.min(y, y + height));
  return {
    x: nx,
    y: ny,
    width: Math.round(Math.abs(width)),
    height: Math.round(Math.abs(height)),
  };
}

function screenToImage(evt, canvas, scale) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: (evt.clientX - rect.left) / scale,
    y: (evt.clientY - rect.top) / scale,
  };
}

function drawBox(ctx, rect, scale, color, label, active = false) {
  if (!rect) return;
  const x = rect.x * scale;
  const y = rect.y * scale;
  const w = rect.width * scale;
  const h = rect.height * scale;
  ctx.save();
  ctx.lineWidth = active ? 4 : 2;
  ctx.strokeStyle = color;
  ctx.fillStyle = `${color}22`;
  ctx.fillRect(x, y, w, h);
  ctx.strokeRect(x, y, w, h);
  ctx.fillStyle = color;
  ctx.font = "700 13px system-ui";
  const text = label || "";
  const textWidth = ctx.measureText(text).width + 10;
  ctx.fillRect(x, Math.max(0, y - 22), textWidth, 22);
  ctx.fillStyle = "#ffffff";
  ctx.fillText(text, x + 5, Math.max(14, y - 7));
  ctx.restore();
}
```

- [ ] **Step 2: Delete the originals from `app.js`**

Remove `slug`, `nowIso`, `box` (lines 57-80), `screenToImage` (82-88) and
`drawBox` (171-191). Then fix the call sites:

- every `screenToImage(evt)` becomes `screenToImage(evt, canvas, state.scale)`
- inside `draw()`, each `drawBox(rect, color, label, active)` becomes
  `drawBox(ctx, rect, state.scale, color, label, active)`

Find them all: `rtk proxy grep -n 'screenToImage\|drawBox' label_web/app.js`

- [ ] **Step 3: Load it in `index.html`**

Before the existing `<script src="app.js"></script>`:

```html
    <script src="boxes.js"></script>
```

- [ ] **Step 4: Verify the labelling page still works**

```bash
rtk proxy python3 -m http.server 8080 --directory label_web
```

Open `http://localhost:8080/`, load any image from `data/templates/`, draw a
logo box and a button box, confirm both render with their labels and that
`Tải JSON xuống` still produces a file. Stop the server.

There is no JS test harness in this repo; this step is the test. Do not skip it —
`drawBox` gained a parameter, and a missed call site draws nothing at all, silently.

- [ ] **Step 5: Commit**

```bash
rtk proxy git add label_web/boxes.js label_web/app.js label_web/index.html
rtk proxy git commit -m "refactor(label_web): share box maths and drawing between pages"
```

---

## Task 11: The review page

**Files:**
- Create: `label_web/review.html`, `label_web/review.js`
- Modify: `label_web/README.md`

**Interfaces:**
- Consumes: `boxes.js` globals; `GET /api/admin/submissions`,
  `GET /api/admin/submissions/{id}`, `POST /api/admin/submissions/{id}/review`.

- [ ] **Step 1: Write `review.html`**

```html
<!doctype html>
<html lang="vi">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>SilverTech — Duyệt mẫu gửi lên</title>
    <link rel="stylesheet" href="styles.css" />
  </head>
  <body>
    <header>
      <h1>Duyệt mẫu gửi lên</h1>
      <p id="connection"></p>
    </header>
    <main>
      <aside>
        <h2>Đang chờ duyệt</h2>
        <ul id="queue"></ul>
      </aside>
      <section>
        <canvas id="canvas" width="960" height="640"></canvas>
        <div id="emptyState">Chọn một mẫu ở cột bên trái.</div>
      </section>
      <aside>
        <h2>Nút bấm</h2>
        <ul id="buttonList"></ul>
        <label>Tên nút (tiếng Việt)<input id="buttonName" /></label>
        <label>Mô tả<input id="buttonUsage" /></label>
        <label>Ghi chú của người duyệt<input id="reviewerNote" /></label>
        <button id="accept">Duyệt</button>
        <button id="reject">Từ chối</button>
        <p id="result"></p>
      </aside>
    </main>
    <script src="boxes.js"></script>
    <script src="review.js"></script>
  </body>
</html>
```

- [ ] **Step 2: Write `review.js`**

```javascript
// label_web/review.js
// Admin review. Served from `python3 -m http.server`, so the origin is
// http://localhost:<port>, which app/main.py's _DEV_ORIGIN_REGEX already allows.
// Opening this file as file:// sends `Origin: null` and every fetch fails.

const params = new URLSearchParams(location.search);
const API = (params.get("api") || "http://localhost:8000").replace(/\/$/, "");
const TOKEN = params.get("token") || localStorage.getItem("silvertech_admin_token") || "";
if (params.get("token")) localStorage.setItem("silvertech_admin_token", params.get("token"));

const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const els = {
  connection: document.getElementById("connection"),
  queue: document.getElementById("queue"),
  emptyState: document.getElementById("emptyState"),
  buttonList: document.getElementById("buttonList"),
  buttonName: document.getElementById("buttonName"),
  buttonUsage: document.getElementById("buttonUsage"),
  reviewerNote: document.getElementById("reviewerNote"),
  accept: document.getElementById("accept"),
  reject: document.getElementById("reject"),
  result: document.getElementById("result"),
};

const state = {
  submissionId: null,
  labels: null,
  image: null,
  scale: 1,
  selected: null,
  drawing: null,
  edited: false,
};

async function api(path, options = {}) {
  const response = await fetch(API + path, {
    ...options,
    headers: { "X-Admin-Token": TOKEN, "Content-Type": "application/json", ...options.headers },
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(`${response.status}: ${detail.message_vi || detail.detail || path}`);
  }
  return response.json();
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!state.image) return;
  canvas.width = Math.round(state.image.width * state.scale);
  canvas.height = Math.round(state.image.height * state.scale);
  ctx.drawImage(state.image, 0, 0, canvas.width, canvas.height);

  drawBox(ctx, state.labels.template.logo_bbox, state.scale, "#c27803", "logo");
  state.labels.buttons.forEach((button, index) => {
    drawBox(
      ctx,
      button.bbox_template_coordinates,
      state.scale,
      "#256fb3",
      button.vietnamese_name || button.button_id,
      index === state.selected,
    );
  });
  if (state.drawing) drawBox(ctx, state.drawing, state.scale, "#cc3b3b", "moi");
}

function renderButtons() {
  els.buttonList.innerHTML = "";
  state.labels.buttons.forEach((button, index) => {
    const item = document.createElement("li");
    const pick = document.createElement("button");
    pick.textContent = `${button.button_id} — ${button.vietnamese_name || "(chưa đặt tên)"}`;
    pick.addEventListener("click", () => {
      state.selected = index;
      els.buttonName.value = button.vietnamese_name || "";
      els.buttonUsage.value = button.function_description || "";
      draw();
    });
    item.appendChild(pick);
    els.buttonList.appendChild(item);
  });
}

async function loadQueue() {
  els.queue.innerHTML = "";
  try {
    const rows = await api("/api/admin/submissions?status=pending");
    els.connection.textContent = `${API} — ${rows.length} mẫu đang chờ`;
    for (const row of rows) {
      const item = document.createElement("li");
      const pick = document.createElement("button");
      pick.textContent = `${row.brand} ${row.appliance_type}`;
      pick.addEventListener("click", () => loadSubmission(row.id));
      item.appendChild(pick);
      els.queue.appendChild(item);
    }
  } catch (error) {
    els.connection.textContent = String(error);
  }
}

async function loadSubmission(submissionId) {
  const detail = await api(`/api/admin/submissions/${submissionId}`);
  state.submissionId = submissionId;
  state.labels = detail.proposed_labels_json;
  state.selected = null;
  state.edited = false;
  els.result.textContent = "";

  const image = new Image();
  image.crossOrigin = "anonymous";
  image.onload = () => {
    state.image = image;
    state.scale = Math.min(1, 960 / image.width);
    els.emptyState.style.display = "none";
    renderButtons();
    draw();
  };
  image.src = `${API}/${detail.image_url}`;
}

canvas.addEventListener("pointerdown", (evt) => {
  if (state.selected === null || !state.image) return;
  const start = screenToImage(evt, canvas, state.scale);
  state.drawing = box(start.x, start.y, 0, 0);
  state.origin = start;
});

canvas.addEventListener("pointermove", (evt) => {
  if (!state.drawing) return;
  const now = screenToImage(evt, canvas, state.scale);
  state.drawing = box(state.origin.x, state.origin.y, now.x - state.origin.x, now.y - state.origin.y);
  draw();
});

canvas.addEventListener("pointerup", () => {
  if (!state.drawing) return;
  if (state.drawing.width > 4 && state.drawing.height > 4) {
    state.labels.buttons[state.selected].bbox_template_coordinates = state.drawing;
    state.edited = true;
  }
  state.drawing = null;
  draw();
});

for (const [input, field] of [
  [els.buttonName, "vietnamese_name"],
  [els.buttonUsage, "function_description"],
]) {
  input.addEventListener("input", () => {
    if (state.selected === null) return;
    state.labels.buttons[state.selected][field] = input.value;
    state.edited = true;
    renderButtons();
    draw();
  });
}

els.accept.addEventListener("click", async () => {
  if (!state.submissionId) return;
  const payload = state.edited
    ? { decision: "edit", edited_template: state.labels, reviewer_note: els.reviewerNote.value || null }
    : { decision: "accept", reviewer_note: els.reviewerNote.value || null };
  try {
    const result = await api(`/api/admin/submissions/${state.submissionId}/review`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    els.result.textContent = `Đã duyệt. template_id: ${result.template_id}`;
    await loadQueue();
  } catch (error) {
    els.result.textContent = String(error);
  }
});

els.reject.addEventListener("click", async () => {
  if (!state.submissionId) return;
  try {
    await api(`/api/admin/submissions/${state.submissionId}/review`, {
      method: "POST",
      body: JSON.stringify({ decision: "reject", reviewer_note: els.reviewerNote.value || null }),
    });
    els.result.textContent = "Đã từ chối.";
    await loadQueue();
  } catch (error) {
    els.result.textContent = String(error);
  }
});

loadQueue();
```

- [ ] **Step 3: Exercise it against a real API**

Terminal 1:

```bash
conda activate silvertech
SILVERTECH_ADMIN_TOKEN=demo-token make run-api
```

`.env` is read by `env_loader`, which only sets a key **absent** from
`os.environ` (`app/services/env_loader.py:20`), so an inline variable wins and a
`--reload` restart does not pick up an edited `.env`.

Terminal 2 — file a submission with a real photo:

```bash
IMAGE_URL=$(curl -s -F image=@data/templates/panasonic_microwave_nn_gt35hm.png \
  http://localhost:8000/api/submissions/image | python3 -c 'import json,sys; print(json.load(sys.stdin)["image_url"])')

python3 - "$IMAGE_URL" <<'PY'
import json, sys, urllib.request
image_url = sys.argv[1]
reviewed = json.load(open("data/templates/labels/panasonic_microwave_nn_gt35hm_v1.json"))
payload = {
    "brand": "Panasonic",
    "appliance_type": "microwave",
    "image_url": image_url,
    "proposed_labels_json": {
        "device": reviewed["device"],
        "template": {
            "template_code": "demo_review_v1",
            "template_image_url": image_url,
            "logo_bbox": reviewed["template"]["logo_bbox"],
            "panel_bbox": reviewed["template"]["panel_bbox"],
        },
        "buttons": reviewed["buttons"][:3],
    },
}
request = urllib.request.Request(
    "http://localhost:8000/api/submissions",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)
print(urllib.request.urlopen(request).read().decode())
PY
```

Terminal 3:

```bash
rtk proxy python3 -m http.server 8080 --directory label_web
```

Open `http://localhost:8080/review.html?token=demo-token`. Confirm, in order:

1. The queue lists one Panasonic microwave.
2. Clicking it draws the panel photo with an orange `logo` box and three blue
   button boxes.
3. Clicking a button in the right column selects it; dragging on the canvas
   moves its box; the list label updates when you retype the name.
4. **Duyệt** prints a `template_id` and the queue empties.
5. `rtk proxy sqlite3 apps/api/silvertech.sqlite3 "SELECT count(*) FROM button_offsets WHERE template_id LIKE 'template_%'"` grew by 3.

Then check the token guard: reload `review.html` with no `?token=` after running
`localStorage.clear()` in the console — the queue must show a `401`, not a list.

- [ ] **Step 4: Document it in `label_web/README.md`**

Append:

```markdown
## Reviewing user submissions

`review.html` lists submissions filed by the mobile wizard, draws their boxes
over the panel photo, lets you fix them, and accepts or rejects the submission.
Accepting writes a real template: `devices`, `templates`, `buttons` and
`button_offsets`, plus a copy of the photo under `data/templates/`.

```bash
SILVERTECH_ADMIN_TOKEN=<a long random string> make run-api
python3 -m http.server 8080 --directory label_web
```

Open `http://localhost:8080/review.html?token=<the same string>`. The token is
kept in `localStorage` after the first load.

Serve the page; do not open it as a `file://` URL. `file://` sends
`Origin: null`, which the API's CORS policy rejects. Override the backend with
`?api=https://...` if it is not on `http://localhost:8000`.
```

- [ ] **Step 5: Commit**

```bash
rtk proxy git add label_web/review.html label_web/review.js label_web/README.md
rtk proxy git commit -m "feat(label_web): review and promote user submissions"
```

---

## Task 12: Documentation

**Files:**
- Modify: `docs/backend-api.md`
- Modify: `docs/known-limitations.md`

- [ ] **Step 1: Read both files**

```bash
rtk proxy cat docs/backend-api.md
rtk proxy grep -n "submission" docs/known-limitations.md
```

- [ ] **Step 2: Add the endpoints to `docs/backend-api.md`**

Follow the existing table or heading style in that file. Document, in whatever
shape the file already uses:

- `GET /api/admin/submissions?status=pending` — header `X-Admin-Token`
- `GET /api/admin/submissions/{id}` — adds `proposed_labels_json`
- `POST /api/admin/submissions/{id}/review` — now returns `template_id` on
  accept/edit; 409 when already reviewed
- `SILVERTECH_ADMIN_TOKEN` unset means every `/api/admin` route answers 503

- [ ] **Step 3: Correct `docs/known-limitations.md`**

Remove any claim that submissions cannot become templates. Add:

```markdown
- `/api/admin/*` is guarded only by the shared secret in `SILVERTECH_ADMIN_TOKEN`.
  Accepting a submission writes the `templates` table the app serves from and
  copies a file onto the host. There is no rate limit and no user identity. The
  ngrok tunnel stays off outside demos.
- A submission becomes a template only when an admin accepts it in
  `label_web/review.html`. The mobile device card still shows no pending state;
  see the spec for that work.
```

- [ ] **Step 4: Run everything**

```bash
rtk proxy env PYTHONPATH=apps/api:apps/vision-tools pytest -q apps/api/tests tests/contract apps/vision-tools/tests
rtk proxy ruff check apps/api
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
rtk proxy git add docs/backend-api.md docs/known-limitations.md
rtk proxy git commit -m "docs: describe admin review and its authentication"
```

---

## Out of scope

- The mobile side: `DemoDevice.submissionId`, the "Chờ duyệt" badge, polling
  `GET /api/admin/submissions/{id}`. That is spec 2, written after this contract
  has run.
- `data/brands/`. `_detect_best_template` crops the logo out of the template's
  own image, so a promoted template is detectable without the SIFT gallery.
- The device library vanishing on browser refresh
  (`JsonFileDeviceLibraryStore`, no `path_provider_web`). Unrelated bug.
