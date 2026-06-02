# SilverTech

SilverTech is an elderly-first mobile assistant for operating household
appliance control panels. The MVP uses reviewed appliance templates,
logo-guided template matching, confidence checks, Vietnamese voice/text queries,
and validated `button_id` guidance.

## Current MVP Scope

- Backend API with SQLite seed data for reviewed appliance templates.
- Mock STT and mock LLM flow for local development.
- `button_id` validation before guidance is returned.
- Offline vision proof of concept for feature matching, confidence scoring, and
  homography/affine button projection.
- Flutter/Dart mobile source scaffold for camera, overlay, guidance, and
  fallback UI.

The MVP does not use QR anchors as the primary localization method and does not
train a custom button detector.

## Local Setup

```bash
conda env create -f environment.yml
conda activate silvertech
export PATH="$HOME/development/flutter/bin:$PATH"
cp .env.example .env
python3 -m pip install -e apps/api
python3 -m pip install -e apps/vision-tools
make seed-api
make run-api
```

Open API docs at `http://127.0.0.1:8000/docs`.

## Demo Flow

1. Seed the database with `make seed-api`.
2. Request candidate templates with `POST /api/vision/candidates`.
3. Request template details with `GET /api/templates/{id}`.
4. Send a Vietnamese query to `POST /api/query`.
5. Verify returned steps reference only valid `button_id` values.
6. Run `make test-vision` to validate projection and low-confidence behavior on
   synthetic fixtures.

## Validation Commands

```bash
conda activate silvertech
PYTHONPATH=apps/api:apps/vision-tools pytest -q apps/api/tests tests/contract apps/vision-tools/tests
dart run apps/mobile/test/vision/homography_projector_test.dart
dart run apps/mobile/test/guidance/instruction_player_test.dart
dart run apps/mobile/test/ui/rescan_guidance_ui_test.dart
cd apps/mobile && flutter test
```

## Current Limitations

- STT and LLM providers are mocked by default. Provider adapters are configured
  but not connected to real external credentials in this repo.
- Flutter is installed at `$HOME/development/flutter`; add
  `$HOME/development/flutter/bin` to PATH before running Flutter commands.
  Chrome/web validation is not required for the Android MVP.
- OpenCV is installed in the `silvertech` environment. Synthetic fixture tests
  still use deterministic keypoint arrays so confidence and projection behavior
  remain stable in CI.
- Real appliance photos must be added under `data/templates/` before a public
  demo with actual camera images.
