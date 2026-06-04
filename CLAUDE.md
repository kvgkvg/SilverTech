# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

SilverTech is an elderly-first mobile assistant for operating household appliance control panels. A user points the camera at an appliance panel; the app matches it to a reviewed template, projects button locations onto the live frame, accepts a Vietnamese voice/text query, and returns step-by-step guidance where every step references a validated `button_id`.

The MVP uses logo-guided template matching with confidence checks (NOT QR anchors, NOT a custom-trained button detector). STT is mocked in the backend and runs on-device in the mobile app; LLM guidance is mocked by default for local development and can use OpenRouter when configured.

## Environment & Commands

Always work inside the `silvertech` conda env (Python 3.12 + dart-sdk).

```bash
conda env create -f environment.yml   # first time
conda activate silvertech
cp .env.example .env
python3 -m pip install -e apps/api
python3 -m pip install -e apps/vision-tools
```

Common targets (see `Makefile`):

```bash
make seed-api      # seed SQLite DB from app.storage.seed_data
make run-api       # uvicorn on 127.0.0.1:8000 (docs at /docs)
make test-api      # API + contract tests
make test-vision   # vision-tools tests
make test          # both
make smoke         # seed + query-flow + invalid-button-id tests
```

Run a single test (note `PYTHONPATH` is required — packages run via path, not install):

```bash
PYTHONPATH=apps/api pytest -q apps/api/tests/test_query_flow.py::test_name
PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_confidence.py
```

Full validation (mirrors README), including Dart logic tests:

```bash
PYTHONPATH=apps/api:apps/vision-tools pytest -q apps/api/tests tests/contract apps/vision-tools/tests
dart run apps/mobile/test/vision/homography_projector_test.dart
dart run apps/mobile/test/guidance/instruction_player_test.dart
dart run apps/mobile/test/ui/rescan_guidance_ui_test.dart
```

Lint: ruff, `line-length = 100` (configured in `apps/api/pyproject.toml`).

## Architecture

Monorepo with three apps under `apps/`:

- **`apps/api`** — FastAPI backend (`app/`). Entry `app/main.py` registers routers and calls `initialize_database()` at import time.
- **`apps/vision-tools`** — Offline OpenCV/numpy proof-of-concept for the matching pipeline (`scripts/`). Not wired into the API; validates projection + confidence on synthetic fixtures.
- **`apps/mobile`** — Flutter/Dart scaffold (`lib/`). Source + a few Dart logic tests only; full Flutter build is NOT set up in this repo (Flutter unavailable from conda channels).

### Backend layering (`apps/api/app`)

`api/` (routers, thin) → `services/` (logic) → `storage/` (SQLite). Schemas in `schemas/`, DB row models in `models/`.

Key flow — **guidance** (`POST /api/query`, `services/guidance_service.py`):
1. Load template (`template_repository.get_template`) → 404 if missing.
2. Build prompt summary, call `LLMService().generate()`.
3. Parse response, then **`validate_guidance_buttons`** rejects any step whose `button_id` is not in the template's valid button IDs → 409.
4. Every attempt (accepted/rejected) is written to `llm_logs` with latency.

The `button_id` validation gate is the core correctness invariant: guidance must never reference a button that doesn't exist on the matched template.

### Storage

Raw `sqlite3` (no ORM at runtime), schema as a single `SCHEMA_SQL` string in `storage/database.py` applied idempotently via `initialize_database()`. SQLAlchemy/Alembic are `prod`-only optional deps (`pyproject.toml`), not used by the dev/SQLite path. DB path from `SILVERTECH_DB_PATH` (default `apps/api/silvertech.sqlite3`). Seed data in `storage/seed_data.py`.

Core tables: `devices` → `templates` → `buttons`; plus `submissions` (user-proposed templates, review workflow), `llm_logs`, `vision_logs`.

### Mock and OpenRouter providers

`SILVERTECH_STT_PROVIDER` and `SILVERTECH_LLM_PROVIDER` default to `mock`. In mock mode, `services/llm_service.py` is a keyword matcher over the Vietnamese query (no real API call). To use OpenRouter, set `SILVERTECH_LLM_PROVIDER=openrouter`, `OPENROUTER_API_KEY`, and `OPENROUTER_MODEL=qwen/qwen3.7-plus`. The backend still validates every returned `button_id` against the matched official template before returning guidance.

### Vision pipeline (offline POC, `apps/vision-tools/scripts`)

`offline_match.match_and_project`: ORB features → descriptor match → homography estimate → reprojection error → `score_confidence` (accept/reject) → `project_buttons`. Tests use deterministic keypoint arrays, not real images, so confidence/projection behavior stays stable. The mobile app re-implements this projection logic in Dart (`lib/vision/`).

## Spec-driven workflow

This repo uses Spec Kit. The active feature spec, plan, data model, and task list live in `specs/001-camera-voice-guidance/`. `AGENTS.md` points to `specs/001-camera-voice-guidance/plan.md` as the source of truth for technical decisions. Supporting docs in `docs/` (e.g. `cv-matching-pipeline.md`, `llm-guidance-schema.md`, `button-labeling-guidelines.md`, `known-limitations.md`). API contract in `apps/api/openapi.yaml`.

## Known limitations

Backend STT is mocked; backend LLM is mocked unless OpenRouter credentials are configured. Flutter build pending on a Flutter-capable machine; vision tests use synthetic fixtures; real appliance photos must be added under `data/templates/` before a real-device demo.

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->
