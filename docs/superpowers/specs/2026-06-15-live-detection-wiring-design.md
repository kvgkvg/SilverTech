# Live Detection Wiring — Design

**Date:** 2026-06-15
**Feature branch:** `003-real-live-detection`
**Maps to:** `specs/003-real-live-detection/plan.md` → Phase **P3 (Live client)**
(the user refers to this work as "P4").

## Problem

The mobile app shows a live camera **preview** but never sends frames anywhere.
The recognition button calls `recognizeDefault()`, which returns a **hardcoded**
template (`template_panasonic_microwave_nn_gt35hm_v1`) with a **fake** match score
(`0.94`). The real ORB matching endpoint (`POST /api/vision/match`) works and is
verified, but **nothing in the app calls it**. There is no real-time detection in
the app today.

This design wires the camera to the real backend matcher: grab frames ~1 fps,
POST them to `/api/vision/match`, and drive the UI from the real
accepted/rejected result plus the backend-returned projected button polygons.

## Goals

- Real camera frames → real backend ORB match → real UI state (no hardcoded
  template, no fake score).
- Cross-platform-safe frame capture; **Web/Chrome is the first verified target**.
- Keep the `button_id` validation gate (guidance) unchanged downstream.

## Non-goals (YAGNI / deferred)

- Native camera frame source (`frame_source_io.dart`, `camera` plugin
  `takePicture`) — deferred; target is web first.
- Continuous optical-flow tracking (smooth AR) — plan workstream W6.
- Multi-template real data (plan P2) — only `panasonic_microwave` matches a real
  photo today; it is the single demo template.
- Resized template image / logging hardening — plan P5.

## Architecture

```
Chrome webcam ─getUserMedia→ <video> ─canvas.drawImage→ JPEG bytes
   │  FrameSource.grabFrame()   (~1 fps, drop in-flight frames)
   ▼
DetectionController ─POST multipart→ /api/vision/match ─ORB→ {accepted, polygons, score}
   ├ accepted (stable: 2 consecutive) → fetch template → overlay polygons
   │                                    → "Đã nhận diện" → [Tiếp tục] → voice/guidance
   └ rejected → recovery hint ("đưa gần hơn / giảm chói") → keep scanning
```

### Components

**1. `lib/vision/vision_match_client.dart` (new)**
- `Future<VisionMatchResult> match(Uint8List jpegBytes, {String? brand, String? applianceType})`
- POSTs `multipart/form-data` to `/api/vision/match`: `file` part (JPEG bytes) +
  optional `brand` / `appliance_type` form fields.
- Parses `VisionMatchResponse` into
  `VisionMatchResult { bool accepted, String? templateId, double? matchScore,
  List<ProjectedButton> projectedButtons, String? failureReason }`.
- Reuses `ProjectedButton` / `geometry.dart` (do not redefine polygon types).
- Error handling mirrors `template_repository_client.dart` `_throwIfError`
  (nested `detail` unwrap).

**2. `lib/vision/frame_source.dart` (new) + impls**
- Interface:
  ```dart
  abstract class FrameSource {
    Future<void> start();
    Future<Uint8List> grabFrame();   // current frame as JPEG bytes
    Future<void> stop();
  }
  ```
- Factory via conditional import, mirroring the existing `stt_factory` pattern:
  - `frame_source_web.dart` — `getUserMedia` → `<video>` → `<canvas>.drawImage`
    → `toBlob`/`toDataURL` JPEG → bytes. Web-only (`dart:html` / `package:web`).
  - `frame_source_file.dart` — reads a bundled panel image asset and returns its
    bytes on each `grabFrame()`. No hardware; used for dev/unit tests and the
    Linux-desktop fallback.
  - `frame_source_factory.dart` — `kIsWeb ? web : file` for now (native `io`
    impl deferred).

**3. `lib/vision/detection_controller.dart` (new)**
- Pure Dart logic, **no Flutter widgets** (unit-testable).
- Depends on a `FrameSource` and a matcher callback/`VisionMatchClient`.
- `start()` → `Timer.periodic(1s)`; each tick, if not `_inFlight`: `grabFrame()`
  → `match()` → emit state. Overlapping ticks are dropped while a request is in
  flight.
- Emits `DetectionState { DetectionPhase phase, double? matchScore,
  List<ProjectedButton> polygons, String? templateId, String? failureReason }`
  via a `ValueNotifier<DetectionState>`; `phase ∈ {scanning, matched, rejected}`.
- Lock-on: declare `matched` only after **2 consecutive** accepted frames (anti-
  flicker). Keeps re-confirming while locked; surfaces live `matchScore`.
- `stop()` cancels the timer and stops the frame source; idempotent.

**4. `lib/backend/silver_backend.dart` (edit)**
- Add `Future<VisionMatchResult> match(Uint8List jpeg, {brand, applianceType})`
  delegating to `VisionMatchClient`.
- Keep `recognizeDefault()` for the file-fallback / no-camera demo path.

**5. `main.dart` camera screen (edit)**
- Replace the hardcoded `_acceptBackendRecognition()` flow with a
  `DetectionController`-driven loop:
  - On camera screen open: `controller.start()`.
  - `scanning` → show "Đang quét…" + live score.
  - `matched` → fetch full template by `templateId`, set the **real** match score,
    overlay the backend-returned polygons on the preview, show "Đã nhận diện
    Panasonic microwave" + **[Tiếp tục]** (elderly-first: confirm, don't auto-jump).
  - `rejected` → recovery hint; keep scanning.
  - On navigate-away / dispose: `controller.stop()`.
- Overlay renders backend `projectedButtons` polygons (replaces the Dart-side
  static projection for the live path).

## Data flow & invariants

- The `button_id` validation gate in `guidance_service.py` (409 on unknown
  button) is **unchanged**. Detection only selects the template; guidance
  correctness is still enforced downstream.
- Frame cadence ~1 fps with in-flight drop bounds backend load to ≤1 concurrent
  match request per client.

## Error handling

- Decode/camera-permission failure in `FrameSource.start()` → surfaced as a
  user-facing message; fall back to file source or RemotePanel placeholder.
- `match()` HTTP error → controller emits `rejected` with `failureReason`; the
  loop continues (a transient failure must not kill the scan).
- Backend `accepted=false` → `rejected` phase + `failureReason` → recovery hint.

## Testing

Honest constraint: the **build/CI sandbox has no camera**; the live webcam path
is verified by the user on Chrome.

- `flutter test` (runnable in this repo):
  - `vision_match_client` — `MockClient`: parses `accepted` + polygons; error
    path unwraps nested `detail`.
  - `detection_controller` — fake `FrameSource` (canned bytes) + fake matcher:
    `scanning → matched` after 2 accepts; drops in-flight frames; `stop()` clean
    and idempotent; transient match error → `rejected`, loop survives.
  - `frame_source_file` — returns non-empty bytes.
- Backend `/api/vision/match` already verified (self-match accepts 798 inliers;
  noise rejects).
- **User-verified:** `flutter run -d chrome` with a real webcam pointed at the
  Panasonic microwave panel → live overlay.

## Risks

1. **Web camera capture plumbing** (getUserMedia → canvas → JPEG) is the main
   client unknown; isolated behind `FrameSource`, verified hands-on on Chrome.
2. **Real ORB thresholds** under live lighting/angle may reject; tunable at the
   `match_images` call site (already localized to `min_inlier_ratio=0.10`).
3. Single real template (panasonic_microwave) — coverage is one panel until
   plan P2 adds more.
