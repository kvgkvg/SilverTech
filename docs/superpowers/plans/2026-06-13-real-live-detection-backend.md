# Real Live Detection — Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the scripted/mock detection + guidance with a real, tested backend: foundation correctness fixes, a real-image OpenCV matching endpoint (`POST /api/vision/match`), a descriptor-build tool, and real OpenRouter LLM wiring.

**Architecture:** The Flutter client (built in a separate plan) posts a JPEG frame ~1×/sec to `POST /api/vision/match`. The endpoint runs real ORB feature matching against precomputed template descriptors, estimates a RANSAC homography, gates on confidence, projects button bounding boxes into frame coordinates, and returns polygons. Guidance stays on `POST /api/query` but now talks to a real OpenRouter LLM. Detection (where buttons are) and guidance (which button_id to press) remain decoupled.

**Tech Stack:** Python 3.12, FastAPI, raw sqlite3, OpenCV (`opencv-python`), numpy, pytest. The existing `apps/vision-tools` matching primitives are reused; the API imports them.

**Scope:** This plan covers **P0 (foundation fixes)** and **P1 (real backend matching + descriptor tooling)** from `specs/003-real-live-detection/plan.md`. P2 (real template data), P3 (cross-platform Flutter client), P4 (end-to-end wiring), and P5 (hardening/UAT) are separate follow-on plans — each depends on the real `/api/vision/match` contract this plan establishes. See "Follow-on plans" at the end.

---

## Pre-flight: dependencies

OpenCV is an *optional* dep and is **not installed** in the current env (`import cv2` fails). The API will import the vision pipeline, so both packages need OpenCV + numpy, and the match endpoint needs multipart support.

- [ ] **Step 0.1: Install OpenCV + numpy + multipart into the `silvertech` env**

```bash
conda activate silvertech
python3 -m pip install "opencv-python>=4.9" "numpy>=1.26" "python-multipart>=0.0.9"
python3 -c "import cv2, numpy; print('cv2', cv2.__version__, 'numpy', numpy.__version__)"
```

Expected: prints a cv2 version (e.g. `cv2 4.x.y numpy 1.26.z`) with no traceback.

- [ ] **Step 0.2: Record the new deps**

Add `numpy>=1.26`, `opencv-python>=4.9`, and `python-multipart>=0.0.9` to `apps/api/pyproject.toml` `dependencies` (the API now does CV work and accepts file uploads):

```toml
dependencies = [
  "fastapi>=0.115",
  "pydantic>=2.0",
  "uvicorn>=0.30",
  "python-multipart>=0.0.9",
  "numpy>=1.26",
  "opencv-python>=4.9",
]
```

- [ ] **Step 0.3: Commit**

```bash
git add apps/api/pyproject.toml
git commit -m "build(api): add opencv, numpy, multipart deps for real matching"
```

---

## P0 — Foundation correctness fixes

These make the *existing* request path correct and ready for a real LLM. They are small and independently valuable. Run API tests with:
`PYTHONPATH=apps/api pytest -q apps/api/tests`

### Task 1: Remove fake latency + fix LLM-failure status code

**Files:**
- Modify: `apps/api/app/services/guidance_service.py:24-25` (delete sleep)
- Modify: `apps/api/app/api/query.py:16-20` (status mapping)
- Test: `apps/api/tests/test_query_error_status.py` (create)

**Why:** `time.sleep(1.2)` on every non-mock request adds fake latency, blocks a worker thread, and corrupts the logged `latency_ms`. And `llm_failed` (provider outage) is currently returned as HTTP 409 Conflict, indistinguishable from "bad guidance" — it should be a 5xx.

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/test_query_error_status.py`:

```python
from __future__ import annotations

import pytest

from app.services import guidance_service


def test_llm_failure_returns_502(client, monkeypatch):
    def boom(self, user_query, template):
        raise guidance_service.LLMProviderError("provider down")

    monkeypatch.setattr(guidance_service.LLMService, "generate", boom)
    response = client.post(
        "/api/query",
        json={
            "template_id": "template_toshiba_washer_panel_v1",
            "user_query_text": "Lam sao de giat nhanh?",
        },
    )
    assert response.status_code == 502
    assert response.json()["detail"]["recovery_action"] == "try_again"
```

- [ ] **Step 2: Run it, verify it fails**

Run: `PYTHONPATH=apps/api pytest -q apps/api/tests/test_query_error_status.py -v`
Expected: FAIL — current code returns 409, not 502.

- [ ] **Step 3: Delete the sleep**

In `apps/api/app/services/guidance_service.py`, remove these two lines (currently 24-25):

```python
    if os.getenv("SILVERTECH_LLM_PROVIDER", "mock").strip().lower() != "mock":
        time.sleep(1.2)
```

If `os` is now unused in the file, also remove `import os` (line 3). `time` is still used for `time.perf_counter()`, keep it.

- [ ] **Step 4: Map `llm_failed` to 502**

In `apps/api/app/api/query.py`, replace the `status` line in the `except` block:

```python
@router.post("/query", response_model=GuidanceOutput)
def query(payload: QueryRequest) -> dict:
    try:
        return create_guidance(payload.template_id, payload.user_query_text)
    except GuidanceError as exc:
        key = str(exc)
        message, action = ERRORS.get(key, ERRORS["invalid_button"])
        if key == "missing_template":
            status = 404
        elif key == "llm_failed":
            status = 502
        else:
            status = 409
        raise friendly_error(status, message, action) from exc
```

- [ ] **Step 5: Run tests, verify pass**

Run: `PYTHONPATH=apps/api pytest -q apps/api/tests/test_query_error_status.py apps/api/tests/test_query_flow.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/services/guidance_service.py apps/api/app/api/query.py apps/api/tests/test_query_error_status.py
git commit -m "fix(api): drop fake LLM latency, return 502 on provider failure"
```

### Task 2: SQLite WAL + busy_timeout

**Files:**
- Modify: `apps/api/app/storage/database.py:105-109`
- Test: `apps/api/tests/test_db_pragmas.py` (create)

**Why:** Every `/api/query` writes `llm_logs` and every detect writes `vision_logs`. With one connection-per-request and no WAL/busy_timeout, concurrent writes raise `sqlite3.OperationalError: database is locked`.

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/test_db_pragmas.py`:

```python
from __future__ import annotations

from app.storage.database import connect


def test_connect_enables_wal_and_busy_timeout(tmp_path, monkeypatch):
    monkeypatch.setenv("SILVERTECH_DB_PATH", str(tmp_path / "pragma.sqlite3"))
    import importlib
    from app.storage import database
    importlib.reload(database)
    conn = database.connect()
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] >= 3000
    finally:
        conn.close()
```

- [ ] **Step 2: Run it, verify it fails**

Run: `PYTHONPATH=apps/api pytest -q apps/api/tests/test_db_pragmas.py -v`
Expected: FAIL — journal_mode is `delete` (default), busy_timeout is `0`.

- [ ] **Step 3: Set the pragmas in `connect()`**

In `apps/api/app/storage/database.py`, replace `connect()`:

```python
def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(database_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn
```

- [ ] **Step 4: Run it, verify pass**

Run: `PYTHONPATH=apps/api pytest -q apps/api/tests/test_db_pragmas.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/storage/database.py apps/api/tests/test_db_pragmas.py
git commit -m "fix(api): enable WAL + busy_timeout to avoid 'database is locked'"
```

### Task 3: OpenRouter `.env.example` keys + adapter unit tests

**Files:**
- Modify: `.env.example`
- Test: `apps/api/tests/test_openrouter_adapter.py` (create)

**Why:** `_generate_openrouter` reads `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`, but `.env.example` documents none of them. And the JSON-extraction helpers (fence stripping, schema-building) are testable without any network call.

- [ ] **Step 1: Add keys to `.env.example`**

Append to `.env.example`:

```bash
# LLM provider: "mock" (default keyword matcher) or "openrouter" (real)
SILVERTECH_LLM_PROVIDER=mock
OPENROUTER_API_KEY=
OPENROUTER_MODEL=google/gemini-2.0-flash-001
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_HTTP_REFERER=
OPENROUTER_APP_TITLE=SilverTech
```

(Keep the existing single `SILVERTECH_LLM_PROVIDER=mock` line — do not duplicate it; edit in place if already present.)

- [ ] **Step 2: Write the failing test**

Create `apps/api/tests/test_openrouter_adapter.py`:

```python
from __future__ import annotations

import pytest

from app.services.llm_service import _parse_json_content, _user_prompt

TEMPLATE = {
    "id": "t1",
    "brand": "Toshiba",
    "appliance_type": "washing_machine",
    "template_code": "toshiba_v1",
    "buttons": [
        {
            "button_id": "quick_wash",
            "label": "Quick",
            "vietnamese_name": "Giat nhanh",
            "function_description": "Chon che do giat nhanh",
        }
    ],
}


def test_user_prompt_lists_valid_button_ids():
    prompt = _user_prompt("Giat nhanh the nao?", TEMPLATE)
    assert "quick_wash" in prompt
    assert "Giat nhanh the nao?" in prompt


def test_parse_json_content_strips_code_fence():
    fenced = '```json\n{"intent": "x", "steps": []}\n```'
    assert _parse_json_content(fenced) == {"intent": "x", "steps": []}


def test_parse_json_content_rejects_non_object():
    with pytest.raises(Exception):
        _parse_json_content("[1, 2, 3]")
```

- [ ] **Step 3: Run it, verify pass**

Run: `PYTHONPATH=apps/api pytest -q apps/api/tests/test_openrouter_adapter.py -v`
Expected: PASS — this is characterization of existing code; if any fail, the bug is in `llm_service.py`, fix there.

- [ ] **Step 4: Commit**

```bash
git add .env.example apps/api/tests/test_openrouter_adapter.py
git commit -m "feat(api): document OpenRouter env keys, add adapter unit tests"
```

### Task 4: Fix mobile guidance-client error parsing (`detail` nesting)

**Files:**
- Modify: `apps/mobile/lib/guidance/guidance_client.dart:30-41`
- Test: `apps/mobile/test/backend_clients_test.dart` (add one test)

**Why:** FastAPI's `friendly_error` nests the payload under `detail` (`{"detail": {"message_vi": ..., "recovery_action": ...}}`). The guidance client reads `body['message_vi']` at the top level, so **every** real 404/409/502 loses its Vietnamese message and falls back to the generic `'Co loi xay ra.'`. The template client already handles `detail` correctly in `_throwIfError`; reuse that shape.

> Note: `backend_clients_test.dart` currently asserts `result.matchScore == 0` (line 51) while `silver_backend.dart` returns `0.94`. That pre-existing assertion may already be red — it is unrelated to this task; do not "fix" it here.

- [ ] **Step 1: Write the failing test**

Add to the `main()` body of `apps/mobile/test/backend_clients_test.dart`:

```dart
  test('guidance client surfaces nested detail message on error', () async {
    final client = GuidanceClient(
      baseUrl: 'http://api.test',
      httpClient: MockClient((http.Request request) async {
        return http.Response(
          jsonEncode(<String, Object?>{
            'detail': <String, Object?>{
              'message_vi': 'Huong dan chua chac chan. Vui long thu lai cau hoi.',
              'recovery_action': 'try_again',
            },
          }),
          409,
        );
      }),
    );

    expect(
      () => client.createGuidance(
        templateId: 'template_daikin_ac_remote_v1',
        userQueryText: 'abc',
      ),
      throwsA(
        isA<FriendlyBackendException>()
            .having((e) => e.messageVi, 'messageVi',
                'Huong dan chua chac chan. Vui long thu lai cau hoi.')
            .having((e) => e.statusCode, 'statusCode', 409),
      ),
    );
  });
```

- [ ] **Step 2: Run it, verify it fails**

Run: `cd apps/mobile && flutter test test/backend_clients_test.dart --plain-name 'surfaces nested detail'`
Expected: FAIL — `messageVi` is `'Co loi xay ra.'`, not the nested message.

(If `flutter` is unavailable on this machine, mark this task blocked and hand it to a Flutter-capable host; do not skip the fix.)

- [ ] **Step 3: Fix the error branch to read `detail`**

In `apps/mobile/lib/guidance/guidance_client.dart`, replace the error block inside `createGuidance`:

```dart
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final decoded = jsonDecode(response.body);
      Map<String, Object?> payload;
      if (decoded is Map<String, Object?> &&
          decoded['detail'] is Map<String, Object?>) {
        payload = decoded['detail'] as Map<String, Object?>;
      } else if (decoded is Map<String, Object?>) {
        payload = decoded;
      } else {
        payload = const <String, Object?>{};
      }
      throw FriendlyBackendException(
        messageVi: payload['message_vi'] as String? ?? 'Co loi xay ra.',
        recoveryAction: payload['recovery_action'] as String? ?? 'try_again',
        statusCode: response.statusCode,
      );
    }
```

- [ ] **Step 4: Run it, verify pass**

Run: `cd apps/mobile && flutter test test/backend_clients_test.dart --plain-name 'surfaces nested detail'`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/mobile/lib/guidance/guidance_client.dart apps/mobile/test/backend_clients_test.dart
git commit -m "fix(mobile): read nested detail payload in guidance error responses"
```

---

## P1 — Real backend matching + descriptor tooling

Run vision tests with: `PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests`
Run API tests with: `PYTHONPATH=apps/api:apps/vision-tools pytest -q apps/api/tests`
(The API imports the `scripts` package from `apps/vision-tools`; that path must be present, matching the README full-validation command.)

### Task 5: Hamming descriptor matcher for real ORB

**Files:**
- Modify: `apps/vision-tools/scripts/match_descriptors.py` (add a function; keep the existing L2 one)
- Test: `apps/vision-tools/tests/test_hamming_matcher.py` (create)

**Why:** `match_descriptors` uses L2 distance (`np.linalg.norm`). ORB descriptors are 32-byte **binary** vectors; their distance metric is **Hamming**. L2 over uint8 bytes produces meaningless matches on real images. Add a Hamming + Lowe-ratio matcher; keep the existing function so the synthetic-array tests (`test_offline_match_regression.py`) stay green.

- [ ] **Step 1: Write the failing test**

Create `apps/vision-tools/tests/test_hamming_matcher.py`:

```python
from __future__ import annotations

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from scripts.match_descriptors import match_descriptors_hamming


def test_hamming_matches_identical_descriptors():
    # Two identical descriptor sets => each row matches its own index.
    desc = np.array(
        [[0, 255, 0, 7], [255, 0, 128, 1], [3, 3, 3, 3]],
        dtype=np.uint8,
    )
    matches = match_descriptors_hamming(desc, desc.copy(), ratio=0.9)
    pairs = {(i, j) for i, j, _ in matches}
    assert (0, 0) in pairs
    assert (1, 1) in pairs


def test_hamming_ratio_test_drops_ambiguous():
    # Query row equidistant-ish to two train rows => ratio test rejects it.
    query = np.array([[0, 0]], dtype=np.uint8)
    train = np.array([[1, 0], [0, 1]], dtype=np.uint8)
    matches = match_descriptors_hamming(query, train, ratio=0.6)
    assert matches == []
```

- [ ] **Step 2: Run it, verify it fails**

Run: `PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_hamming_matcher.py -v`
Expected: FAIL — `match_descriptors_hamming` does not exist.

- [ ] **Step 3: Implement the Hamming matcher**

Append to `apps/vision-tools/scripts/match_descriptors.py`:

```python
def match_descriptors_hamming(
    query_desc: "np.ndarray",
    train_desc: "np.ndarray",
    *,
    ratio: float = 0.75,
) -> list[tuple[int, int, float]]:
    """Match binary (ORB) descriptors with BFMatcher(NORM_HAMMING) + Lowe ratio.

    Returns (query_index, train_index, distance) for surviving matches.
    """
    import cv2

    if query_desc is None or train_desc is None:
        return []
    if len(query_desc) == 0 or len(train_desc) < 2:
        return []
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    knn = bf.knnMatch(
        np.asarray(query_desc, dtype=np.uint8),
        np.asarray(train_desc, dtype=np.uint8),
        k=2,
    )
    good: list[tuple[int, int, float]] = []
    for pair in knn:
        if len(pair) < 2:
            continue
        best, second = pair[0], pair[1]
        if best.distance <= ratio * second.distance:
            good.append((best.queryIdx, best.trainIdx, float(best.distance)))
    return good
```

(Add `import numpy as np` already exists at top of the file — confirm; it does.)

- [ ] **Step 4: Run it, verify pass**

Run: `PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_hamming_matcher.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Confirm synthetic regression still green**

Run: `PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_offline_match_regression.py -v`
Expected: PASS — the old L2 `match_descriptors` is untouched.

- [ ] **Step 6: Commit**

```bash
git add apps/vision-tools/scripts/match_descriptors.py apps/vision-tools/tests/test_hamming_matcher.py
git commit -m "feat(vision): add Hamming + Lowe-ratio matcher for real ORB descriptors"
```

### Task 6: Real-image match function `match_images`

**Files:**
- Create: `apps/vision-tools/scripts/match_images.py`
- Test: `apps/vision-tools/tests/test_match_images.py` (create)
- Test fixtures: `apps/vision-tools/tests/fixtures/panel_template.png`, `apps/vision-tools/tests/fixtures/panel_frame.png` (create — see Step 1)

**Why:** `offline_match.match_and_project` only takes synthetic *point arrays*. Real detection needs an image→image path: real ORB on both images, Hamming match, RANSAC homography, confidence gate, project buttons. Reuse `score_confidence`, `estimate_homography_with_inliers`, and `project_buttons` so thresholds/geometry stay shared.

- [ ] **Step 1: Generate deterministic fixture images**

A real photo isn't needed for the unit test — a synthetic textured panel and a warped copy of it exercise the full real-ORB path deterministically. Create `apps/vision-tools/tests/fixtures/_make_fixtures.py`:

```python
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent


def _panel() -> np.ndarray:
    rng = np.random.default_rng(42)
    img = (rng.integers(0, 60, size=(400, 600), dtype=np.uint8))
    # High-contrast "buttons": filled rectangles with borders => ORB corners.
    boxes = [(60, 40), (260, 40), (460, 40), (160, 220), (360, 220)]
    for (x, y) in boxes:
        cv2.rectangle(img, (x, y), (x + 110, y + 90), 255, -1)
        cv2.rectangle(img, (x + 12, y + 12), (x + 98, y + 78), 0, 4)
    return img


def main() -> None:
    template = _panel()
    cv2.imwrite(str(HERE / "panel_template.png"), template)
    # Frame = template under a mild affine (shift + slight scale/rotation).
    h, w = template.shape
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), 6.0, 1.05)
    matrix[0, 2] += 18
    matrix[1, 2] += 12
    frame = cv2.warpAffine(template, matrix, (w, h), borderValue=20)
    cv2.imwrite(str(HERE / "panel_frame.png"), frame)


if __name__ == "__main__":
    main()
```

Run it to produce the committed fixtures:

```bash
mkdir -p apps/vision-tools/tests/fixtures
PYTHONPATH=apps/vision-tools python3 apps/vision-tools/tests/fixtures/_make_fixtures.py
ls apps/vision-tools/tests/fixtures/
```

Expected: `_make_fixtures.py  panel_frame.png  panel_template.png`.

- [ ] **Step 2: Write the failing test**

Create `apps/vision-tools/tests/test_match_images.py`:

```python
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from scripts.match_images import match_images

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(name: str) -> np.ndarray:
    img = cv2.imread(str(FIXTURES / name), cv2.IMREAD_GRAYSCALE)
    assert img is not None, f"missing fixture {name}"
    return img


def test_match_accepts_warped_copy_and_projects_button():
    template = _load("panel_template.png")
    frame = _load("panel_frame.png")
    buttons = {"start": {"x": 60, "y": 40, "width": 110, "height": 90}}
    result = match_images(template, frame, buttons)
    assert result["accepted"] is True
    poly = result["projected_buttons"]["start"]
    assert len(poly) == 4
    # Projected top-left should land near the warped box (shifted right/down).
    assert poly[0]["x"] > 60
    assert poly[0]["y"] > 40


def test_match_rejects_unrelated_noise():
    template = _load("panel_template.png")
    rng = np.random.default_rng(7)
    noise = rng.integers(0, 255, size=template.shape, dtype=np.uint8)
    result = match_images(template, noise, {"start": {"x": 0, "y": 0, "width": 5, "height": 5}})
    assert result["accepted"] is False
    assert result["failure_reason"] is not None
    assert result["projected_buttons"] == {}
```

- [ ] **Step 3: Run it, verify it fails**

Run: `PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_match_images.py -v`
Expected: FAIL — `scripts.match_images` does not exist.

- [ ] **Step 4: Implement `match_images`**

Create `apps/vision-tools/scripts/match_images.py`:

```python
from __future__ import annotations

from typing import Any

import numpy as np

from scripts.confidence import compute_reprojection_error, score_confidence
from scripts.estimate_transform import estimate_homography_with_inliers, transform_points
from scripts.match_descriptors import match_descriptors_hamming
from scripts.project_buttons import project_buttons

_MIN_MATCHES = 4


def _orb_features(image: np.ndarray):
    import cv2

    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=1500)
    keypoints, descriptors = orb.detectAndCompute(gray, None)
    points = np.array([kp.pt for kp in keypoints], dtype=float)
    return points, descriptors


def _rejected(reason: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    out = {"accepted": False, "failure_reason": reason, "projected_buttons": {}}
    if extra:
        out.update(extra)
    return out


def match_images(
    template_image: np.ndarray,
    frame_image: np.ndarray,
    buttons: dict[str, dict[str, float]],
    *,
    template_keypoints: np.ndarray | None = None,
    template_descriptors: np.ndarray | None = None,
) -> dict[str, Any]:
    """Match a frame against a template by real ORB features and project buttons.

    `template_keypoints`/`template_descriptors` may be supplied (precomputed) to
    skip re-extracting the template every call. Result shape matches
    `offline_match.match_and_project`.
    """
    if template_keypoints is None or template_descriptors is None:
        tpl_pts, tpl_desc = _orb_features(template_image)
    else:
        tpl_pts, tpl_desc = np.asarray(template_keypoints, dtype=float), template_descriptors
    frm_pts, frm_desc = _orb_features(frame_image)

    if tpl_desc is None or frm_desc is None or len(tpl_pts) == 0 or len(frm_pts) == 0:
        return _rejected("low_confidence")

    matches = match_descriptors_hamming(tpl_desc, frm_desc, ratio=0.75)
    if len(matches) < _MIN_MATCHES:
        return _rejected("low_confidence")

    src = np.array([tpl_pts[i] for i, _, _ in matches], dtype=float)
    dst = np.array([frm_pts[j] for _, j, _ in matches], dtype=float)
    matrix, inlier_mask = estimate_homography_with_inliers(src, dst)
    inlier_src = src[inlier_mask]
    inlier_dst = dst[inlier_mask]
    if len(inlier_src) < _MIN_MATCHES:
        return _rejected("low_confidence")

    projected = transform_points(inlier_src, matrix)
    error = compute_reprojection_error(projected, inlier_dst)
    confidence = score_confidence(
        match_count=len(inlier_src),
        total_keypoints=len(tpl_pts),
        reprojection_error=error,
    )
    payload = {
        "match_score": confidence.match_score,
        "inlier_count": confidence.inlier_count,
        "inlier_ratio": confidence.inlier_ratio,
        "reprojection_error": confidence.reprojection_error,
    }
    if not confidence.accepted:
        return _rejected(confidence.failure_reason, payload)
    return {
        "accepted": True,
        "failure_reason": None,
        **payload,
        "matrix": matrix.tolist(),
        "projected_buttons": project_buttons(buttons, matrix),
    }
```

- [ ] **Step 5: Run it, verify pass**

Run: `PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_match_images.py -v`
Expected: PASS (2 tests).

> If `test_match_accepts_...` fails on confidence (real ORB on the synthetic panel may produce a low inlier ratio), this is the **threshold-tuning risk** called out in the spec. Adjust `score_confidence` defaults in a follow-up only with a comment justifying the value against the fixture; do not loosen blindly.

- [ ] **Step 6: Commit**

```bash
git add apps/vision-tools/scripts/match_images.py apps/vision-tools/tests/test_match_images.py apps/vision-tools/tests/fixtures/
git commit -m "feat(vision): real image-to-image ORB match + button projection"
```

### Task 7: Descriptor build tool

**Files:**
- Create: `apps/vision-tools/scripts/build_descriptors.py`
- Test: `apps/vision-tools/tests/test_build_descriptors.py` (create)

**Why:** The match endpoint should load *precomputed* template descriptors (`.npz`) instead of re-extracting ORB from the template image on every request. Only the Panasonic microwave currently has a `.npz`; new templates need a repeatable way to generate one.

- [ ] **Step 1: Write the failing test**

Create `apps/vision-tools/tests/test_build_descriptors.py`:

```python
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from scripts.build_descriptors import build_descriptors, load_descriptors

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_build_and_load_roundtrip(tmp_path):
    out = tmp_path / "panel.npz"
    build_descriptors(str(FIXTURES / "panel_template.png"), str(out))
    keypoints, descriptors = load_descriptors(str(out))
    assert keypoints.shape[1] == 2
    assert len(keypoints) == len(descriptors)
    assert descriptors.dtype == np.uint8
    assert len(keypoints) > 10
```

- [ ] **Step 2: Run it, verify it fails**

Run: `PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_build_descriptors.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement the tool**

Create `apps/vision-tools/scripts/build_descriptors.py`:

```python
from __future__ import annotations

import argparse

import numpy as np


def build_descriptors(image_path: str, out_path: str) -> int:
    """Extract ORB keypoints+descriptors from an image, save to a .npz. Returns count."""
    import cv2

    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"cannot read image: {image_path}")
    orb = cv2.ORB_create(nfeatures=1500)
    keypoints, descriptors = orb.detectAndCompute(img, None)
    if descriptors is None:
        raise ValueError(f"no ORB features in {image_path}")
    points = np.array([kp.pt for kp in keypoints], dtype=np.float32)
    np.savez(out_path, keypoints=points, descriptors=descriptors.astype(np.uint8))
    return len(points)


def load_descriptors(npz_path: str) -> tuple[np.ndarray, np.ndarray]:
    data = np.load(npz_path)
    return data["keypoints"], data["descriptors"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ORB descriptor .npz from a template image")
    parser.add_argument("image")
    parser.add_argument("output")
    args = parser.parse_args()
    count = build_descriptors(args.image, args.output)
    print(f"wrote {count} descriptors to {args.output}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run it, verify pass**

Run: `PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_build_descriptors.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/vision-tools/scripts/build_descriptors.py apps/vision-tools/tests/test_build_descriptors.py
git commit -m "feat(vision): ORB descriptor build/load tool (.npz)"
```

### Task 8: `POST /api/vision/match` endpoint

**Files:**
- Create: `apps/api/app/services/match_service.py`
- Create: `apps/api/app/api/vision_match.py`
- Modify: `apps/api/app/main.py` (register router)
- Modify: `apps/api/app/schemas/templates.py` (add response schema)
- Test: `apps/api/tests/test_vision_match.py` (create)

**Why:** This is the real replacement for the scripted recognition. It accepts an uploaded frame, matches against candidate templates' precomputed descriptors, and returns projected button polygons + confidence, writing a real `vision_log`.

- [ ] **Step 1: Add response schemas**

Append to `apps/api/app/schemas/templates.py`:

```python
class ProjectedButton(BaseModel):
    button_id: str
    polygon: list[Point]


class VisionMatchResponse(BaseModel):
    accepted: bool
    template_id: str | None = None
    match_score: float | None = None
    inlier_count: int | None = None
    inlier_ratio: float | None = None
    reprojection_error: float | None = None
    failure_reason: str | None = None
    recovery_action: str | None = None
    projected_buttons: list[ProjectedButton] = Field(default_factory=list)
```

(Confirm `Field` and `Point` are imported at the top of the file — `Point` is defined there, `Field` is imported from pydantic.)

- [ ] **Step 2: Write the match service**

Create `apps/api/app/services/match_service.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from app.services.template_repository import get_template, list_candidates
from app.storage.database import ROOT

# Reused from the vision-tools package (installed via `pip install -e apps/vision-tools`
# or PYTHONPATH=apps/vision-tools). See README full-validation command.
from scripts.build_descriptors import load_descriptors
from scripts.match_images import match_images

_FAILURE_RECOVERY = {
    "low_confidence": "rescan",
    "no_logo": "scan_wider",
    "glare": "reduce_glare",
    "partial_view": "move_closer",
}


def _decode_gray(image_bytes: bytes) -> "np.ndarray":
    import cv2

    buf = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("could not decode image bytes")
    return img


def _template_assets(template: dict[str, Any]) -> tuple["np.ndarray | None", "np.ndarray | None", "np.ndarray | None"]:
    """Return (template_gray | None, keypoints | None, descriptors | None)."""
    import cv2

    descriptor_url = template.get("feature_descriptor_url")
    if descriptor_url:
        npz_path = ROOT / descriptor_url
        if npz_path.exists():
            kp, desc = load_descriptors(str(npz_path))
            return None, kp, desc
    image_url = template.get("template_image_url")
    if image_url:
        img_path = ROOT / image_url
        if img_path.exists() and img_path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            return cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE), None, None
    return None, None, None


def _buttons_map(template: dict[str, Any]) -> dict[str, dict[str, float]]:
    return {b["button_id"]: b["bbox_template_coordinates"] for b in template.get("buttons", [])}


def match_frame(
    image_bytes: bytes,
    *,
    brand: str | None = None,
    appliance_type: str | None = None,
) -> dict[str, Any]:
    frame = _decode_gray(image_bytes)
    candidates = list_candidates(brand, appliance_type) or list_candidates(None, None)

    best: dict[str, Any] | None = None
    best_template_id: str | None = None
    for summary in candidates:
        template = get_template(summary["id"])
        if template is None or not template.get("buttons"):
            continue
        tpl_gray, kp, desc = _template_assets(template)
        if tpl_gray is None and desc is None:
            continue  # placeholder template with no real image/descriptors
        result = match_images(
            tpl_gray if tpl_gray is not None else np.zeros((1, 1), dtype=np.uint8),
            frame,
            _buttons_map(template),
            template_keypoints=kp,
            template_descriptors=desc,
        )
        if result.get("accepted"):
            if best is None or result["match_score"] > best["match_score"]:
                best = result
                best_template_id = template["id"]

    if best is None:
        return {
            "accepted": False,
            "failure_reason": "low_confidence",
            "recovery_action": "rescan",
            "projected_buttons": [],
        }

    polygons = [
        {"button_id": bid, "polygon": poly}
        for bid, poly in best["projected_buttons"].items()
    ]
    return {
        "accepted": True,
        "template_id": best_template_id,
        "match_score": best["match_score"],
        "inlier_count": best["inlier_count"],
        "inlier_ratio": best["inlier_ratio"],
        "reprojection_error": best["reprojection_error"],
        "projected_buttons": polygons,
    }
```

- [ ] **Step 3: Write the router**

Create `apps/api/app/api/vision_match.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile

from app.schemas.templates import VisionMatchResponse
from app.services.match_service import match_frame
from app.services.vision_log_service import write_vision_log

router = APIRouter(prefix="/api/vision", tags=["vision"])


@router.post("/match", response_model=VisionMatchResponse)
async def match(
    file: UploadFile = File(...),
    brand: str | None = Form(default=None),
    appliance_type: str | None = Form(default=None),
) -> dict:
    image_bytes = await file.read()
    result = match_frame(image_bytes, brand=brand, appliance_type=appliance_type)
    try:
        write_vision_log(
            {
                "template_id": result.get("template_id"),
                "brand_candidate": brand,
                "match_score": result.get("match_score"),
                "inlier_count": result.get("inlier_count"),
                "inlier_ratio": result.get("inlier_ratio"),
                "reprojection_error": result.get("reprojection_error"),
                "accepted": result["accepted"],
                "failure_reason": result.get("failure_reason"),
            }
        )
    except Exception:
        pass  # telemetry must not break detection
    return result
```

- [ ] **Step 4: Register the router**

In `apps/api/app/main.py`, add the import and `include_router`:

```python
from app.api import (
    admin_submissions, docs, query, stt, submissions, templates,
    vision, vision_logs, vision_match,
)
```

and after `app.include_router(vision_logs.router)`:

```python
app.include_router(vision_match.router)
```

- [ ] **Step 5: Write the failing test**

Create `apps/api/tests/test_vision_match.py`:

```python
from __future__ import annotations

from io import BytesIO
from pathlib import Path

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

FIXTURES = Path(__file__).resolve().parents[2] / "vision-tools" / "tests" / "fixtures"


def _jpeg_of(name: str) -> bytes:
    img = cv2.imread(str(FIXTURES / name), cv2.IMREAD_GRAYSCALE)
    assert img is not None
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return buf.tobytes()


def test_match_endpoint_rejects_unknown_frame(client):
    # Random noise should not match any seeded template.
    rng = np.random.default_rng(1)
    noise = rng.integers(0, 255, size=(400, 600), dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", noise)
    response = client.post(
        "/api/vision/match",
        files={"file": ("frame.jpg", BytesIO(buf.tobytes()), "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is False
    assert body["recovery_action"] == "rescan"
    assert body["projected_buttons"] == []
```

> A positive-match endpoint test needs a *seeded* template whose descriptors match the uploaded frame. That depends on real template data (P2). This task ships the reject path (always exercisable) + the full code path; the accept path gets an endpoint test in P2 once a real template+photo pair is seeded.

- [ ] **Step 6: Run it, verify pass**

Run: `PYTHONPATH=apps/api:apps/vision-tools pytest -q apps/api/tests/test_vision_match.py -v`
Expected: PASS — endpoint returns a structured rejection for noise.

- [ ] **Step 7: Full backend suite green**

Run: `PYTHONPATH=apps/api:apps/vision-tools pytest -q apps/api/tests apps/vision-tools/tests`
Expected: PASS (all).

- [ ] **Step 8: Commit**

```bash
git add apps/api/app/services/match_service.py apps/api/app/api/vision_match.py apps/api/app/main.py apps/api/app/schemas/templates.py apps/api/tests/test_vision_match.py
git commit -m "feat(api): real POST /api/vision/match endpoint with ORB matching"
```

---

## Self-review (done by plan author)

- **Spec coverage (P0+P1):** W4 guidance-client/detail (Task 4), time.sleep + status (Task 1), WAL (Task 2), OpenRouter config (Task 3). W1 Hamming fix (Task 5), real match (Task 6), descriptors (Task 7), `/api/vision/match` (Task 8). ✓
- **Deferred to P2–P5 (own plans):** W2 template data, W3 Flutter `FrameSource`/`DetectionController`/overlay, W5 logging+resized image, W6 future. Listed below.
- **Type consistency:** `match_images` returns the same dict keys consumed by `match_service` (`accepted`, `match_score`, `inlier_count`, `inlier_ratio`, `reprojection_error`, `projected_buttons`, `failure_reason`). `VisionMatchResponse.projected_buttons` is `list[ProjectedButton]`; `match_service` emits `{"button_id", "polygon"}` dicts matching that schema. `load_descriptors` returns `(keypoints, descriptors)`, consumed positionally in `_template_assets`. ✓
- **Placeholders:** none — every code step is complete.

## Follow-on plans (write after P1 lands the `/api/vision/match` contract)

1. **P2 — Real template data** (`docs/superpowers/plans/<date>-real-template-data.md`): capture/source 2–3 real panel photos; label with `data/templates/labels/*.json`; run `build_descriptors.py` per template; reseed; **drop the 3 `.txt` placeholder templates** from the seed so the app never offers an unmatchable template; add the positive-match endpoint test deferred in Task 8 Step 5; re-tune `score_confidence` thresholds on real photos.
2. **P3 — Cross-platform Flutter client** (own plan, needs a Flutter host + devices): `FrameSource` interface with conditional-import impls (`frame_source_io.dart` = `camera` package; `frame_source_web.dart` = getUserMedia→canvas→blob), mirroring the existing `stt_factory` pattern; `DetectionController` (~1 fps loop, drop in-flight frames, stop on navigate-away); replace scripted `recognizeDefault()` + static `TemplateDataPanel` with live overlay of `/api/vision/match` polygons; wire `MatchConfidenceState` + recovery prompts.
3. **P4 — End-to-end real path**: matched template → real OpenRouter guidance → step highlight uses the matched button's projected polygon; latency budget < 5 s (spec).
4. **P5 — Hardening/UAT**: replace `print()` telemetry with `logging` (W5); serve a resized template image + `cacheWidth`; failure-case UAT (no panel, glare, wrong brand).
```
