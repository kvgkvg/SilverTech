# Tasks: SilverTech Camera Voice Guidance

**Input**: Design documents from `/specs/001-camera-voice-guidance/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/openapi.yaml`, `quickstart.md`

**Tests**: Included because the specification, plan, and user request require localization, validation, API, failure, and UAT testing.

**Organization**: Tasks are grouped by phase and user story so each story can be implemented and reviewed independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other `[P]` tasks in the same phase after dependencies are met
- **[Story]**: User-story label for story phases only
- Every task includes an exact target file or directory path

## Phase 1: Project Setup

**Purpose**: Create the repository structure and local development foundation.

- [X] T001 Create monorepo directories `apps/mobile/`, `apps/api/`, `apps/vision-tools/`, `data/templates/`, `data/descriptors/`, `data/test-images/`, `tests/contract/`, `tests/e2e/`, and `tests/uat/`
- [ ] T002 Initialize Flutter mobile project in `apps/mobile/`
- [X] T003 Initialize FastAPI backend project with dependency metadata in `apps/api/pyproject.toml`
- [X] T004 Initialize Python vision tooling package with dependency metadata in `apps/vision-tools/pyproject.toml`
- [X] T005 [P] Configure mobile linting and formatting in `apps/mobile/analysis_options.yaml`
- [X] T006 [P] Configure backend linting, formatting, and pytest settings in `apps/api/pyproject.toml`
- [X] T007 [P] Configure vision-tool linting, formatting, and pytest settings in `apps/vision-tools/pyproject.toml`
- [X] T008 Add root development commands for mobile, API, tests, and vision tools in `Makefile`
- [X] T009 Add environment variable examples for API, STT, LLM, storage, and SQLite path in `.env.example`
- [X] T010 Add local setup and run instructions in `README.md`
- [X] T011 Add shared OpenAPI contract copy or reference from `specs/001-camera-voice-guidance/contracts/openapi.yaml` to `apps/api/openapi.yaml`

**Checkpoint**: Project skeleton is ready for schema, API, vision, and mobile implementation.

---

## Phase 2: Foundational Data, Backend, and Offline Vision

**Purpose**: Build blocking infrastructure required before any user story can safely ship.

**Critical**: Complete this phase before user-story implementation. Button localization must work on reviewed templates before crowdsourcing or advanced tracking.

### Database And Seed Data

- [X] T012 Create SQLAlchemy database session and settings module in `apps/api/app/storage/database.py`
- [X] T013 Create migration environment and configuration in `apps/api/alembic/env.py`
- [X] T014 Create Device model and migration for `devices` in `apps/api/app/models/device.py`
- [X] T015 Create Template model and migration for `templates` in `apps/api/app/models/template.py`
- [X] T016 Create Button model and migration for `buttons` in `apps/api/app/models/button.py`
- [X] T017 Create Submission model and migration for `submissions` in `apps/api/app/models/submission.py`
- [X] T018 Create LLMLog model and migration for `llm_logs` in `apps/api/app/models/llm_log.py`
- [X] T019 Create VisionLog model and migration for `vision_logs` in `apps/api/app/models/vision_log.py`
- [X] T020 Add database enum and JSON validation helpers in `apps/api/app/models/common.py`
- [X] T021 Add seed fixture metadata for 2-3 official appliance templates in `apps/api/app/storage/seed_data.py`
- [X] T022 Add sample template image placeholders or documented image slots in `data/templates/README.md`
- [X] T023 Add sample button coordinate JSON for seeded templates in `data/templates/button_coordinates.sample.json`
- [X] T024 Add seed command to create official devices, templates, and buttons in `apps/api/app/storage/seed.py`
- [X] T025 [P] Add schema validation tests for devices/templates/buttons in `apps/api/tests/test_schema_models.py`
- [X] T026 [P] Add migration smoke test for SQLite schema creation in `apps/api/tests/test_migrations.py`

### Backend Foundation

- [X] T027 Create FastAPI application entrypoint and router registration in `apps/api/app/main.py`
- [X] T028 Create Pydantic schemas for templates, buttons, errors, and guidance output in `apps/api/app/schemas/templates.py`
- [X] T029 Create shared friendly Vietnamese error response helpers in `apps/api/app/schemas/errors.py`
- [X] T030 Create template repository service for official templates and buttons in `apps/api/app/services/template_repository.py`
- [X] T031 Create privacy-aware logging configuration in `apps/api/app/services/logging_config.py`
- [X] T032 Add generated API documentation route metadata from `apps/api/openapi.yaml` in `apps/api/app/api/docs.py`
- [X] T033 [P] Add backend app startup test in `apps/api/tests/test_app_startup.py`

### Computer Vision Proof Of Concept

- [X] T034 Create image loading and coordinate JSON loader in `apps/vision-tools/scripts/load_inputs.py`
- [X] T035 Create ORB keypoint and descriptor extraction script in `apps/vision-tools/scripts/extract_orb_features.py`
- [X] T036 Create descriptor matching and good-match filtering script in `apps/vision-tools/scripts/match_descriptors.py`
- [X] T037 Create RANSAC homography estimation script in `apps/vision-tools/scripts/estimate_transform.py`
- [X] T038 Create confidence scoring module for match score, inlier count, inlier ratio, reprojection error, and geometry checks in `apps/vision-tools/scripts/confidence.py`
- [X] T039 Create button box projection module in `apps/vision-tools/scripts/project_buttons.py`
- [X] T040 Create still-image visualization output script in `apps/vision-tools/scripts/visualize_projection.py`
- [X] T041 Add unreliable-match failure handling in `apps/vision-tools/scripts/offline_match.py`
- [X] T042 Add optional SIFT comparison path when available in `apps/vision-tools/scripts/compare_orb_sift.py`
- [X] T043 [P] Add coordinate transformation unit tests in `apps/vision-tools/tests/test_project_buttons.py`
- [X] T044 [P] Add confidence scoring unit tests in `apps/vision-tools/tests/test_confidence.py`
- [X] T045 [P] Add sample image matching regression tests in `apps/vision-tools/tests/test_offline_match_regression.py`
- [X] T046 [P] Add failure image regression tests for glare, blur, partial panel, wrong brand, and low confidence in `apps/vision-tools/tests/test_failure_cases.py`

**Checkpoint**: Official template data exists, the backend can start, and the offline CV pipeline can accept/reject stored images before live mobile work begins.

---

## Phase 3: User Story 1 - Get Guided Help From Camera and Voice (Priority: P1)

**Goal**: A user scans a supported panel, asks a Vietnamese question, receives validated steps, and sees the correct current-step button highlighted.

**Independent Test**: On a supported washing machine panel, ask "Làm sao để giặt nhanh?" and verify the app shows one large Vietnamese step at a time and highlights only validated buttons from the matched template.

### Tests For User Story 1

- [X] T047 [P] [US1] Add contract tests for `GET /api/templates/{id}` and `POST /api/vision/candidates` in `tests/contract/test_template_contract.py`
- [X] T048 [P] [US1] Add contract tests for `POST /api/stt` and `POST /api/query` in `tests/contract/test_guidance_contract.py`
- [X] T049 [P] [US1] Add LLM JSON validation unit tests in `apps/api/tests/test_llm_validation.py`
- [X] T050 [P] [US1] Add backend query-flow integration test with valid Vietnamese query and seeded template in `apps/api/tests/test_query_flow.py`
- [X] T051 [P] [US1] Add mobile coordinate projection unit tests in `apps/mobile/test/vision/homography_projector_test.dart`
- [X] T052 [P] [US1] Add mobile widget test for large current-step instruction rendering in `apps/mobile/test/guidance/instruction_player_test.dart`

### Backend APIs And Guidance Implementation

- [X] T053 [US1] Implement template candidate retrieval endpoint `POST /api/vision/candidates` in `apps/api/app/api/vision.py`
- [X] T054 [US1] Implement template detail endpoint `GET /api/templates/{id}` in `apps/api/app/api/templates.py`
- [X] T055 [US1] Implement mock and provider-backed STT service interface in `apps/api/app/services/stt_service.py`
- [X] T056 [US1] Implement STT endpoint `POST /api/stt` in `apps/api/app/api/stt.py`
- [X] T057 [US1] Implement LLM prompt builder constrained to selected template buttons in `apps/api/app/services/llm_prompt_builder.py`
- [X] T058 [US1] Implement LLM provider adapter with mock, Gemini Flash, and GPT-4o-mini configuration slots in `apps/api/app/services/llm_service.py`
- [X] T059 [US1] Implement LLM response parser for intent, ordered steps, `button_id`, expected result, and safety note in `apps/api/app/services/llm_response_parser.py`
- [X] T060 [US1] Implement `button_id` validator against matched template buttons in `apps/api/app/services/button_validator.py`
- [X] T061 [US1] Implement invalid LLM output regeneration/error handling in `apps/api/app/services/guidance_service.py`
- [X] T062 [US1] Implement query endpoint `POST /api/query` in `apps/api/app/api/query.py`
- [X] T063 [US1] Implement LLM log persistence for query text, STT text, prompt summary, raw response, validated steps, status, and latency in `apps/api/app/services/llm_log_service.py`
- [X] T064 [US1] Register US1 routers in `apps/api/app/main.py`

### Mobile Scanning, Vision, And AR Overlay

- [X] T065 [US1] Implement elderly-friendly home entry and launch-to-camera path in `apps/mobile/lib/screens/home_screen.dart`
- [X] T066 [US1] Implement camera scanning screen with Vietnamese instruction text in `apps/mobile/lib/screens/camera_screen.dart`
- [X] T067 [US1] Implement frame capture pipeline for analysis frames in `apps/mobile/lib/vision/frame_capture_pipeline.dart`
- [X] T068 [US1] Implement simple brand selection and logo/brand matching placeholder in `apps/mobile/lib/vision/brand_matcher.dart`
- [X] T069 [US1] Implement backend candidate template client in `apps/mobile/lib/templates/template_repository_client.dart`
- [X] T070 [US1] Implement on-device ORB/SIFT matching bridge or service wrapper in `apps/mobile/lib/vision/vision_matcher.dart`
- [X] T071 [US1] Implement homography/affine projection for button boxes in `apps/mobile/lib/vision/homography_projector.dart`
- [X] T072 [US1] Implement overlay renderer for projected button boxes and current-step highlight in `apps/mobile/lib/vision/overlay_renderer.dart`
- [X] T073 [US1] Implement confidence gate state that blocks highlights until accepted in `apps/mobile/lib/vision/match_confidence_state.dart`
- [X] T074 [US1] Implement voice record button and audio capture state in `apps/mobile/lib/voice/voice_input.dart`
- [X] T075 [US1] Implement STT client with mock/provider API modes in `apps/mobile/lib/voice/stt_client.dart`
- [X] T076 [US1] Implement guidance query client for `POST /api/query` in `apps/mobile/lib/guidance/guidance_client.dart`
- [X] T077 [US1] Implement instruction player with large Vietnamese text and current step state in `apps/mobile/lib/guidance/instruction_player.dart`
- [X] T078 [US1] Implement next/previous step controls in `apps/mobile/lib/guidance/step_controls.dart`
- [X] T079 [US1] Implement button highlight binding from current guidance step `button_id` to projected button boxes in `apps/mobile/lib/guidance/highlight_controller.dart`
- [X] T080 [US1] Implement platform TTS playback for instruction text in `apps/mobile/lib/voice/tts_manager.dart`
- [X] T081 [US1] Wire camera, template retrieval, matching, voice query, steps, and overlay on `apps/mobile/lib/screens/camera_screen.dart`

**Checkpoint**: US1 is MVP-demonstrable on at least one supported official template.

---

## Phase 4: User Story 2 - Recover Safely When Recognition Is Uncertain (Priority: P2)

**Goal**: The app refuses to guess under low confidence or unsupported conditions and gives elderly-friendly recovery instructions.

**Independent Test**: Present glare, blur, low light, partial panel, wrong brand, no logo, similar templates, invalid query, and invalid `button_id` outputs; verify no confident highlight appears and recovery UI is shown.

### Tests For User Story 2

- [X] T082 [P] [US2] Add backend invalid `button_id` rejection tests in `apps/api/tests/test_invalid_button_id_handling.py`
- [X] T083 [P] [US2] Add mobile low-confidence rescan UI widget tests in `apps/mobile/test/ui/rescan_guidance_ui_test.dart`
- [X] T084 [P] [US2] Add e2e failure-flow checklist for glare, blur, partial panel, wrong brand, and low confidence in `tests/e2e/failure_flows.md`

### Safe Fallback Implementation

- [X] T085 [US2] Implement Vietnamese rescan guidance messages for move closer, reduce glare, scan wider, manual select, type query, and try again in `apps/mobile/lib/ui/rescan_guidance_ui.dart`
- [X] T086 [US2] Implement manual brand/template selection fallback in `apps/mobile/lib/ui/manual_template_selection_ui.dart`
- [X] T087 [US2] Implement reset tracking button and state reset in `apps/mobile/lib/vision/tracking_reset_controller.dart`
- [X] T088 [US2] Implement optional optical-flow tracking after accepted match in `apps/mobile/lib/vision/optical_flow_tracker.dart`
- [X] T089 [US2] Implement tracking confidence drop detection and overlay shutdown in `apps/mobile/lib/vision/tracking_confidence_monitor.dart`
- [X] T090 [US2] Implement unsupported task and invalid query error rendering in `apps/mobile/lib/guidance/guidance_error_view.dart`
- [X] T091 [US2] Implement typed Vietnamese query fallback in `apps/mobile/lib/voice/typed_query_input.dart`
- [X] T092 [US2] Implement vision log ingestion endpoint for accepted and rejected matches in `apps/api/app/api/vision_logs.py`
- [X] T093 [US2] Implement vision log persistence with failure reasons in `apps/api/app/services/vision_log_service.py`
- [X] T094 [US2] Connect mobile low-confidence states to vision log submission in `apps/mobile/lib/vision/vision_log_client.dart`
- [X] T095 [US2] Add friendly backend error mapping for invalid guidance, STT failure, and missing template in `apps/api/app/schemas/errors.py`

**Checkpoint**: US2 can be validated independently with failure inputs and must never show an unverified highlight.

---

## Phase 5: User Story 3 - Maintain a Reviewed Template Library (Priority: P3)

**Goal**: Maintainers can submit and review new templates without letting unreviewed templates drive official guidance.

**Independent Test**: Submit a new panel image and button labels, verify it remains pending, accept/edit/reject it, and verify only accepted templates become official and versioned.

### Tests For User Story 3

- [X] T096 [P] [US3] Add contract tests for `POST /api/submissions` in `tests/contract/test_submission_contract.py`
- [X] T097 [P] [US3] Add contract tests for `POST /api/admin/submissions/{id}/review` in `tests/contract/test_admin_review_contract.py`
- [X] T098 [P] [US3] Add backend tests that submitted templates are excluded from runtime candidates in `apps/api/tests/test_submission_review_status.py`

### Submission And Review Implementation

- [X] T099 [US3] Implement submission creation endpoint `POST /api/submissions` in `apps/api/app/api/submissions.py`
- [X] T100 [US3] Implement panel-image-only submission validation in `apps/api/app/services/submission_validation_service.py`
- [X] T101 [US3] Implement submission storage service for image path and proposed labels JSON in `apps/api/app/services/submission_service.py`
- [X] T102 [US3] Implement admin review endpoint `POST /api/admin/submissions/{id}/review` in `apps/api/app/api/admin_submissions.py`
- [X] T103 [US3] Implement review service that accepts, edits, rejects, versions templates, and creates official buttons in `apps/api/app/services/review_service.py`
- [X] T104 [US3] Implement mobile or maintainer submission form placeholder in `apps/mobile/lib/templates/template_submission_screen.dart`
- [X] T105 [US3] Implement admin review UI placeholder or documented local review workflow in `apps/mobile/lib/templates/admin_review_screen.dart`
- [X] T106 [US3] Register submission and admin routers in `apps/api/app/main.py`

**Checkpoint**: US3 expands coverage through reviewed data only; no submitted template is official until accepted.

---

## Phase 6: UX, Accessibility, Documentation, And Final Integration

**Purpose**: Cross-cutting polish, documentation, UAT, and final demo readiness.

### UX And Accessibility

- [X] T107 [P] Audit mobile text sizes, contrast, touch targets, and one-tap actions in `apps/mobile/lib/ui/accessibility_audit.dart`
- [X] T108 [P] Add reusable elderly-friendly button, text, and panel styles in `apps/mobile/lib/ui/silvertech_theme.dart`
- [X] T109 [P] Add friendly full-screen error states in `apps/mobile/lib/ui/friendly_error_screen.dart`

### Documentation

- [X] T110 [P] Document template data format in `docs/template-data-format.md`
- [X] T111 [P] Document button labeling guidelines in `docs/button-labeling-guidelines.md`
- [X] T112 [P] Document CV matching pipeline and confidence thresholds in `docs/cv-matching-pipeline.md`
- [X] T113 [P] Document backend API usage in `docs/backend-api.md`
- [X] T114 [P] Document LLM prompt strategy and output schema in `docs/llm-guidance-schema.md`
- [X] T115 [P] Document known limitations and out-of-scope MVP items in `docs/known-limitations.md`
- [X] T116 [P] Document final presentation demo script in `docs/demo-script.md`
- [X] T117 [P] Add manual UAT checklist for elderly or elderly-like users in `tests/uat/manual-uat-checklist.md`

### Final Integration And Release Readiness

- [X] T118 Connect mobile scanning to backend template retrieval in `apps/mobile/lib/screens/camera_screen.dart`
- [X] T119 Connect matched template ID to backend query endpoint in `apps/mobile/lib/guidance/guidance_client.dart`
- [X] T120 Connect returned guidance steps to AR overlay current-step highlight in `apps/mobile/lib/guidance/highlight_controller.dart`
- [X] T121 Wire vision and LLM event logging across mobile and API in `apps/mobile/lib/telemetry/event_logger.dart`
- [X] T122 Run quickstart validation and record results in `specs/001-camera-voice-guidance/quickstart-results.md`
- [ ] T123 Run end-to-end demo on at least one real appliance and record evidence in `tests/e2e/real-device-demo.md`
- [X] T124 Fix critical demo-blocking bugs found during E2E/UAT in `docs/critical-bug-log.md`
- [X] T125 Prepare Android MVP build notes and artifact checklist in `docs/release-build.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies; start immediately.
- **Phase 2 Foundational**: Depends on Phase 1; blocks all user stories.
- **Phase 3 US1**: Depends on Phase 2; MVP priority and must be completed before final demo.
- **Phase 4 US2**: Depends on Phase 2 and integrates with US1 matching/overlay states; can begin after US1 interfaces are stable.
- **Phase 5 US3**: Depends on Phase 2 database/API foundation; can proceed after US1/US2 MVP behavior is stable because crowdsourcing is lower priority.
- **Phase 6 Polish/Integration**: Depends on desired user stories; final E2E requires US1 and US2.

### User Story Dependencies

- **US1 (P1)**: Core MVP. Can start after Phase 2 and produces camera-to-guidance demo.
- **US2 (P2)**: Safety fallback layer. Depends on shared matching confidence data and mobile overlay state from US1, but its failure flows are independently testable.
- **US3 (P3)**: Template maintenance. Depends on shared schema and template repository, but not required for first MVP demo.

### Within Each Story

- Tests should be written before implementation tasks when practical.
- Backend schema/services before endpoints.
- Candidate retrieval and template detail before mobile live retrieval.
- Offline vision confidence before live overlay.
- Valid `button_id` validation before rendering or speaking guidance.
- Confidence gates before any AR highlight is shown.

### Parallel Opportunities

- Setup lint/config tasks T005-T007 can run in parallel.
- Schema tests T025-T026 and backend startup test T033 can run after models/config are in place.
- Offline CV modules T034-T042 can be split by file after fixtures are defined.
- US1 tests T047-T052 can be written in parallel.
- US1 backend tasks T053-T064 and mobile tasks T065-T081 can proceed in parallel once API schemas are agreed.
- US2 tests T082-T084 can be written in parallel with fallback UI tasks.
- US3 contract tests T096-T098 can be written in parallel with submission/review services.
- Documentation tasks T110-T117 can run in parallel near the end.

---

## Parallel Examples

### User Story 1

```text
Task: T047 Contract tests for template APIs in tests/contract/test_template_contract.py
Task: T048 Contract tests for STT/query APIs in tests/contract/test_guidance_contract.py
Task: T049 LLM JSON validation tests in apps/api/tests/test_llm_validation.py
Task: T051 Mobile projection tests in apps/mobile/test/vision/homography_projector_test.dart
```

```text
Task: T053 Implement candidate endpoint in apps/api/app/api/vision.py
Task: T066 Implement camera screen in apps/mobile/lib/screens/camera_screen.dart
Task: T070 Implement mobile vision matcher in apps/mobile/lib/vision/vision_matcher.dart
Task: T077 Implement instruction player in apps/mobile/lib/guidance/instruction_player.dart
```

### User Story 2

```text
Task: T082 Invalid button_id tests in apps/api/tests/test_invalid_button_id_handling.py
Task: T083 Rescan UI tests in apps/mobile/test/ui/rescan_guidance_ui_test.dart
Task: T085 Rescan UI in apps/mobile/lib/ui/rescan_guidance_ui.dart
Task: T092 Vision log endpoint in apps/api/app/api/vision_logs.py
```

### User Story 3

```text
Task: T096 Submission contract tests in tests/contract/test_submission_contract.py
Task: T097 Admin review contract tests in tests/contract/test_admin_review_contract.py
Task: T099 Submission endpoint in apps/api/app/api/submissions.py
Task: T103 Review service in apps/api/app/services/review_service.py
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 US1 until one supported panel works end to end.
3. Complete the US2 low-confidence paths needed to prevent wrong highlights.
4. Run the final integration tasks T118-T123 for one real appliance demo.
5. Defer US3 crowdsourcing if it threatens localization reliability.

### Incremental Delivery

1. Static templates and offline CV proof.
2. Live scan and overlay with confidence gates.
3. Vietnamese query, validated steps, and current-step highlight.
4. Safety fallbacks for bad scans and invalid guidance.
5. Review workflow for expanding template coverage.

### Quality Gates

- No AR highlight without reviewed template data, accepted match confidence, and valid `button_id` traceability.
- No submitted template becomes official without review.
- No MVP demo counts unless at least one real appliance task succeeds end to end.
- No release candidate without glare/blur/partial/wrong-brand/low-confidence failure tests.

## Notes

- Prioritize button localization via logo-guided template matching before crowdsourcing or advanced tracking.
- Keep MVP coverage small: 2-3 real appliance panels, washing machines first.
- Do not add QR-anchor dependency or custom button detector training in MVP.
- Keep user-facing recovery text simple, Vietnamese, large, and high contrast.
