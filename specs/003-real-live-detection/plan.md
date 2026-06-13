# Implementation Plan: Real App — Live Backend Detection

**Branch**: TBD (`003-real-live-detection`) | **Date**: 2026-06-13
**Supersedes parts of**: [001 plan.md](../001-camera-voice-guidance/plan.md)
**Status**: Proposed — awaiting review

## Goal

Turn the current scripted demo into a real, no-mock application:

- **Live camera detection** runs against a real OpenCV matching pipeline (not a
  hardcoded template at a fake 0.94 confidence).
- **Guidance** comes from a real LLM (OpenRouter), not the keyword mock.
- **Templates** are real, captured-and-labeled appliance panels with real
  feature descriptors (not 70-byte `.txt` placeholders).

## Decisions (locked 2026-06-13)

| Question | Decision | Consequence |
|---|---|---|
| Target platform | **All / cross-platform** (phone + web + desktop, one codebase) | Forces backend matching; needs a platform-abstracted frame source |
| Where matching runs | **Backend** — new `POST /api/vision/match` wraps the existing Python CV pipeline | Reuses real code, works everywhere; client always needs network to the API |
| Live fidelity | **Periodic re-detect ~1 fps** | Snapshot every ~0.7–1 s, re-project boxes. No optical-flow tracking this round |
| LLM provider | **OpenRouter** (adapter already coded) | Supply `OPENROUTER_API_KEY` + model, flip `SILVERTECH_LLM_PROVIDER=openrouter` |

This **changes a core 001 decision**: 001 chose *on-device* OpenCV. We move
matching to the backend so a single Flutter codebase can run on web and desktop
(the demo targets) as well as phones. On-device/offline tracking remains a
documented future upgrade (see Phase 6), not MVP scope.

## Architecture

```
            ┌─────────────────────────── Flutter client (one codebase) ──────────────────────────┐
            │  FrameSource (platform-abstracted)        DetectionLoop (~1 fps)                     │
camera ──▶  │   - mobile/desktop: `camera` controller    captures JPEG ─┐                          │
            │   - web: getUserMedia → canvas → blob                     │                          │
            │                                                           ▼                          │
            │  OverlayRenderer  ◀── projected polygons ── BackendGateway.match(frameBytes, hints)   │
            └───────────────────────────────────────────────────────────┬──────────────────────────┘
                                                                         │ multipart JPEG
                                                                         ▼
            ┌───────────────────────────── FastAPI backend ──────────────────────────────┐
            │ POST /api/vision/match                                                      │
            │   decode → ORB(frame) → BFMatcher(Hamming) vs candidate template descriptors│
            │   → findHomography(RANSAC) → confidence gate → project button bboxes        │
            │   → write vision_log → return {template_id, confidence, button polygons}    │
            │   or {accepted:false, failure_reason, recovery_action}                      │
            │                                                                            │
            │ POST /api/query  → real OpenRouter LLM → button_id validation → steps        │
            └────────────────────────────────────────────────────────────────────────────┘
```

Detection and guidance stay decoupled: detection returns *which template + where
its buttons are on screen*; guidance returns *which button_id to press*. The
overlay highlights the guidance step's `button_id` using the polygon detection
produced for that same template.

## Workstreams

### W1 — Backend real-image matching (the core new code)

The offline POC matches synthetic point arrays. Real images need a real path.

- New `match_images(template_img, frame_img, buttons) -> result` in
  `apps/vision-tools/scripts/` (or `offline_match.match_and_project` extended to
  accept images): real ORB on both images, `BFMatcher(NORM_HAMMING, crossCheck)`,
  Lowe ratio filter, `findHomography(RANSAC)`, reuse `score_confidence` +
  `project_buttons`.
- **Fix `match_descriptors`**: it uses L2 (`np.linalg.norm`) — wrong for ORB
  binary descriptors. Use Hamming. Keep the synthetic-array path for existing
  deterministic tests behind a branch or a separate function.
- Precomputed template descriptors: load from `feature_descriptor_path` (`.npz`)
  to avoid re-extracting the template every request. Provide a tool to (re)build
  descriptors from a template image.
- `POST /api/vision/match`: accept multipart image + optional `brand` /
  `appliance_type` hints; filter candidate templates (reuse `list_candidates`);
  return the projected-polygon payload or a friendly recovery error; write a
  real `vision_log` (real `match_score`, `inlier_count`, etc.).
- Tests: real fixture images (one template + a photo/render of it) asserting
  accept-with-projection and reject-on-mismatch. **Re-tune thresholds on real
  images** — values in `score_confidence` (min_inliers 4, ratio 0.5, reproj 5.0)
  were set for synthetic fixtures and will likely need adjustment.

### W2 — Real template data

- Capture or source clear photos of 2–3 real panels (reuse the existing
  Panasonic microwave as #1 — it already has a real PNG, `.npz`, and labels).
- Label buttons with the existing `data/templates/labels/*.json` schema; seed via
  the existing `seed.py` label loader.
- Generate + commit `.npz` descriptors per template.
- Replace the `.txt` placeholder templates (or drop them from the seed so the app
  never offers an unmatchable template).
- Document the capture→label→descriptor process in `docs/`.

### W3 — Cross-platform frame source + detection loop (client)

- `FrameSource` interface: `Future<Uint8List> grabFrame()` + lifecycle.
  Conditional-import impls mirroring the existing `stt_factory` pattern:
  - `frame_source_io.dart` — `camera` package (mobile + desktop) `takePicture`
    or throttled image stream.
  - `frame_source_web.dart` — getUserMedia → `<canvas>` → `toBlob`.
- `DetectionController`: ~1 fps loop → `grabFrame()` → `backend.match(...)` →
  emit `MatchConfidenceState` + projected polygons; debounce, drop in-flight
  frames, stop on navigate-away.
- Replace scripted `recognizeDefault()` and the static `TemplateDataPanel`
  hardcoded boxes with live overlay of backend-returned polygons over the camera
  preview.
- Confidence gate + recovery prompts already exist in spirit (`MatchConfidenceState`,
  `friendly_error` recovery actions) — wire them to the real states.
- **Note** cross-platform camera is the client risk: Flutter `camera` support on
  Linux desktop is weak and web needs getUserMedia. The `FrameSource`
  abstraction contains this, but each platform needs its own verification.

### W4 — Real LLM (OpenRouter) + guidance correctness fixes

- Config: `SILVERTECH_LLM_PROVIDER=openrouter`, `OPENROUTER_API_KEY`,
  `OPENROUTER_MODEL` in `.env`; verify one real round-trip.
- **Fix `guidance_client.dart` error parsing**: it reads `body['message_vi']`
  top-level, but `friendly_error` nests under `detail`. Today every real
  404/409 loses its Vietnamese message. Reuse the `_throwIfError` logic from
  `template_repository_client.dart`.
- **Remove `time.sleep(1.2)`** in `guidance_service.py` — it adds fake latency to
  real calls, blocks a worker, and corrupts logged `latency_ms`.
- **Fix error status**: `llm_failed` (provider outage) currently returns 409;
  return 502/503 so clients can distinguish "retry later" from "bad guidance".
- Separate the bare `except Exception` in `create_guidance` so malformed-LLM-JSON
  vs invalid-`button_id` are logged distinctly (`error` vs `rejected`), enabling
  a future regenerate-retry (the `regenerated` status already exists in schema).

### W5 — Storage + endpoint hardening

- Add `PRAGMA journal_mode=WAL` + `busy_timeout` in `connect()` — every query
  writes `llm_logs` and every detect writes `vision_logs`; concurrent writes will
  hit "database is locked" without this.
- Replace `print()` telemetry in `vision.py` / `vision_logs.py` with `logging`.
- Serve a resized derivative of the 16.5 MB template PNG (and set `cacheWidth` on
  the client `Image.network`) so the client doesn't decode a ~98 MB RGBA bitmap.

### W6 — Future (explicitly out of MVP scope)

- Continuous optical-flow tracking (upgrade from ~1 fps to smooth AR) — revisits
  the on-device/hybrid path; the `optical_flow_tracker.dart` / `tracking_*`
  stubs are the placeholders.
- Submission → official-template promotion: `review_service.review_submission`
  accepts a submission but never creates a device/template/buttons (returns
  `template_id: None`). The crowdsource half of the data model is currently
  write-only. Needed before real community templates, not before the demo.
- Auth on `/api/admin/*` (currently open).

## Phasing

| Phase | Deliverable | Gate |
|---|---|---|
| **P0** Foundation fixes | W4 guidance-client/detail + time.sleep + status fixes; W5 WAL/busy_timeout. Existing path becomes correct & real-LLM-ready. | `make test` green; one real OpenRouter query returns validated steps |
| **P1** Backend matching | W1 real-image `match_images` + `POST /api/vision/match` + Hamming fix + real-fixture tests | Endpoint accepts a real panel photo, rejects a mismatch, returns projected polygons |
| **P2** Template data | W2 2–3 real labeled templates + descriptors seeded | Each template matches its own photo above threshold |
| **P3** Live client | W3 `FrameSource` + `DetectionController` + live overlay; replace scripted recognition | Real device/web frame → real overlay on at least one platform |
| **P4** End-to-end real | Wire matched template → real guidance → step highlights matched button's projected polygon | Full ask→guidance path real, < 5 s (spec perf goal) |
| **P5** Hardening/UAT | Failure cases (no panel, glare, wrong brand), latency budget, resized image, logging | UAT script passes on the supported panels |

## Top risks

1. **Real ORB thresholds.** Confidence gates tuned on synthetic data may reject
   real photos or accept wrong ones. P1/P2 must re-tune with real images — this
   is the #1 technical unknown.
2. **Cross-platform camera.** Web getUserMedia + Linux desktop camera are the
   fragile spots; `FrameSource` isolates them but each needs hands-on testing.
3. **Template data bottleneck.** Real matching needs real, well-lit panel photos;
   without physical access (or good source images) coverage stalls at 1 panel.
4. **1 fps + network.** Each detect costs a round-trip; fine for "it found the
   buttons", not smooth AR. Acceptable per the locked decision.

## Out of scope (this plan)

On-device/offline matching, optical-flow tracking, submission promotion, admin
auth, additional appliance categories, iOS-specific polish.
