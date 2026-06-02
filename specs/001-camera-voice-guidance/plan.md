# Implementation Plan: SilverTech Camera Voice Guidance

**Branch**: `001-camera-voice-guidance` | **Date**: 2026-06-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-camera-voice-guidance/spec.md`

## Summary

Build a mobile-first MVP that lets elderly Vietnamese users scan an appliance
control panel, ask a Vietnamese question, and receive step-by-step guidance with
the correct button highlighted on the live camera view. The technical approach
uses Flutter for the mobile app, OpenCV-backed on-device template matching and
projection, a FastAPI service for templates/STT/LLM validation workflows, and a
small SQLite-backed template database for MVP development with PostgreSQL
compatibility for later deployment.

## Technical Context

**Language/Version**: Dart 3.x / Flutter 3.x for mobile; Python 3.12 for backend and tooling

**Primary Dependencies**: Flutter camera stack, OpenCV bindings/native module, FastAPI, SQLAlchemy, Pydantic, Google STT or Zalo ASR adapter, Gemini Flash or GPT-4o-mini adapter, platform TTS

**Storage**: SQLite for MVP and local demos; PostgreSQL-compatible schema for deployment; filesystem/object storage paths for template images and feature descriptors

**Testing**: Flutter widget/integration tests; pytest for backend and vision tooling; stored-image vision regression tests; manual UAT scripts for elderly or elderly-like users

**Target Platform**: Low-to-mid-range Android phones first; backend service on a local or cloud Linux environment; iOS deferred until MVP behavior is proven

**Project Type**: Mobile app + backend API + shared vision/template data artifacts

**Performance Goals**: Users see either a guidance step or a recovery instruction within 5 seconds after asking; live camera feedback remains near-real-time during scanning; accepted matches meet overlap and safety criteria from the spec

**Constraints**: No QR-anchor dependency; no custom button detector training in MVP; no confident highlight below threshold; only valid `button_id` values can drive guidance; capture/submission images must be appliance-panel-only

**Scale/Scope**: MVP supports 2-3 reviewed real appliance panels, prioritizing washing machines; crowdsource/admin flow is basic review, not a marketplace

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Elderly-first UX**: PASS. The mobile app opens to scanning, uses one-step
  guidance, large Vietnamese text, clear next-step controls, and simple
  recovery prompts. MVP excludes login and complex configuration.
- **Button safety**: PASS. The plan defines confidence thresholds, validation
  of projected button regions, tracking reset, and backend `button_id`
  validation before any instruction can be highlighted.
- **Localization approach**: PASS. The primary method is logo-guided template
  matching with ORB/SIFT feature matching, RANSAC homography/affine alignment,
  and projection of reviewed template coordinates. QR anchors are explicitly
  out of scope.
- **Template source of truth**: PASS. The data model defines devices,
  templates, buttons, submissions, LLM logs, and vision logs. Runtime guidance
  references only reviewed template button IDs.
- **Hybrid architecture**: PASS. Camera acquisition, matching, projection,
  tracking, and overlay run on-device where feasible. STT, LLM, template
  search, logs, and review workflows run in the backend.
- **Performance and robustness**: PASS. The plan includes match confidence,
  inlier count, inlier ratio, reprojection error, geometric plausibility,
  low-light/glare/partial-view failures, and tracking reset behavior.
- **Privacy and data minimization**: PASS. Submissions and debug images are
  limited to appliance control panels; logs minimize voice/LLM content and are
  retained only for debugging/evaluation.
- **Testability and MVP discipline**: PASS. The artifacts define unit,
  integration, vision regression, failure, and UAT tests. MVP coverage is
  limited to 2-3 real panels.

## Project Structure

### Documentation (this feature)

```text
specs/001-camera-voice-guidance/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── openapi.yaml
└── tasks.md
```

### Source Code (repository root)

```text
apps/
├── mobile/
│   ├── lib/
│   │   ├── screens/
│   │   ├── vision/
│   │   ├── templates/
│   │   ├── guidance/
│   │   ├── voice/
│   │   └── ui/
│   └── test/
├── api/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── storage/
│   └── tests/
└── vision-tools/
    ├── scripts/
    ├── fixtures/
    └── tests/

data/
├── templates/
├── descriptors/
└── test-images/

tests/
├── contract/
├── e2e/
└── uat/
```

**Structure Decision**: Use a monorepo with separate `apps/mobile`,
`apps/api`, and `apps/vision-tools` areas. The mobile app owns camera,
on-device matching, projection, tracking, and AR overlay. The API owns template
metadata, STT/LLM orchestration, `button_id` validation, submissions, admin
review, and logs. Vision tools support offline template seeding and regression
tests against stored images.

## Complexity Tracking

No constitution violations. The mobile app + backend split is required by the
hybrid architecture: near-camera feedback and overlays need local execution,
while STT, LLM validation, template search, review, and logs are centralized for
iteration and governance.

## Implementation Phases

### Phase 1: Static Template and Offline Vision Proof

- Create database schema for devices, templates, buttons, submissions, LLM logs,
  and vision logs.
- Seed 2-3 manually labeled template records and local template images.
- Build offline image matching proof of concept using stored test images.
- Visualize projected button regions on still images and compare against
  manually labeled ground truth.

### Phase 2: Live Mobile Matching and Overlay

- Implement `CameraScreen`, `VisionMatcher`, `TemplateRepositoryClient`,
  `HomographyProjector`, and `OverlayRenderer`.
- Retrieve templates by brand/appliance type and run live candidate matching.
- Add confidence gates, tracking reset, rescan prompts, and manual template
  selection UI.
- Verify the app refuses to highlight when match confidence is low.

### Phase 3: Voice, LLM, and Step Guidance

- Implement Vietnamese voice input, STT fallback to typed input, query API, LLM
  output schema, and `button_id` validation.
- Implement `InstructionPlayer`, step navigation, current-step highlight, and
  optional platform TTS.
- Add failure handling for STT errors and invalid LLM output.

### Phase 4: Review Flow, UAT, and Optimization

- Implement template submission and admin review endpoints/screens.
- Add review-status enforcement before templates become official.
- Run elderly or elderly-like UAT and failure tests for no logo, wrong logo,
  low light, glare, partial panel, similar templates, and invalid `button_id`.
- Optimize matching thresholds and latency for the supported MVP panels.

## Core Localization Pipeline

1. Acquire camera frame on mobile.
2. Detect or match brand/logo using image matching or OCR-based brand matching.
3. Retrieve candidate templates by brand and appliance type when available.
4. Extract ORB/SIFT keypoints/descriptors from frame and candidates.
5. Match features with BFMatcher or FLANN and filter good matches.
6. Estimate homography or affine transform with RANSAC.
7. Compute inlier count, inlier ratio, reprojection error, and geometric
   plausibility.
8. Select best candidate only if confidence thresholds pass.
9. Project button bounding boxes/polygons into camera-frame coordinates.
10. Track with optical flow or periodic rematching and reset on confidence drop.
11. Draw the AR highlight for the current validated guidance step.

## Post-Design Constitution Check

- **Elderly-first UX**: PASS. Quickstart and mobile modules include one-step
  guidance, rescan prompts, manual selection fallback, large Vietnamese text,
  and optional TTS.
- **Button safety**: PASS. Data model, API contract, and tests require valid
  template status, `button_id` validation, confidence gates, and no highlight on
  low confidence.
- **Localization approach**: PASS. Research and plan select logo-guided
  template matching with ORB/SIFT and homography/affine projection, not QR.
- **Template source of truth**: PASS. `data-model.md` defines the source tables
  and validation rules, and `contracts/openapi.yaml` exposes template/buttons
  as the guidance source.
- **Hybrid architecture**: PASS. Mobile and API responsibilities are separated
  explicitly.
- **Performance and robustness**: PASS. Research, quickstart, and tests cover
  near-real-time feedback, low-light/glare/partial views, tracking reset, and
  latency logging.
- **Privacy and data minimization**: PASS. Data model and API contract restrict
  panel submissions and logs.
- **Testability and MVP discipline**: PASS. The artifacts preserve 2-3 real
  panel scope and define measurable validation paths.
