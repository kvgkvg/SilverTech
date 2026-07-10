# SilverTech

SilverTech is an elderly-first mobile assistant for operating household
appliance control panels. The MVP uses reviewed appliance templates,
logo-guided template matching, confidence checks, Vietnamese voice/text queries,
and validated `button_id` guidance.

**Data link**: https://drive.google.com/drive/folders/1JwesdumQ9GoQBLPNvIU4FEUvrY0AW4lO?usp=sharing

## Development Team & Roles

| Member | Student ID | Roles | Core Responsibilities |
| :--- | :--- | :--- | :--- |
| **Bui Anh Quan** | 23122017 | Project Manager (PM), Business Analyst (BA), QA Tester | Project coordination, requirements gathering, API contracts design, integration testing |
| **Luu Thuong Hong** | 23122006 | Mobile & AI Integration Developer | Flutter camera integration, client-side vision logic, platform bridging, STT/TTS wireframe |
| **Nguyen Thien An** | 23122020 | Backend & Data Pipeline Developer | FastAPI services, LLM orchestration, structured prompt engineering, validation logic |
| **Le Nguyen Khang** | 23122034 | Database Administrator (DBA) | SQLite schema design, relational constraints, log auditing, template seeding, migrations |
| **Nguyen Ngoc Khoa** | 23122036 | UI/UX Designer | User journey definition, high-contrast elderly UI/UX layouts, AR highlight guidelines |

## Current MVP Scope

- Backend API with SQLite seed data for reviewed appliance templates.
- On-device Vietnamese STT in the mobile app (sherpa-onnx zipformer-vi-30M
  int8); mock LLM flow for local development. Backend `/api/stt` mock retained
  but unused by the app.
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

- LLM provider is mocked by default. Provider adapters are configured but not
  connected to real external credentials in this repo.
- Mobile STT runs fully on-device via sherpa-onnx. The model files
  (~32 MB) are not committed; download them into
  `apps/mobile/assets/models/asr/` before `flutter build` (see that dir's
  README). The legacy backend `/api/stt` mock is no longer called by the app.
- Flutter is installed at `$HOME/development/flutter`; add
  `$HOME/development/flutter/bin` to PATH before running Flutter commands.
  Chrome/web validation is not required for the Android MVP.
- OpenCV is installed in the `silvertech` environment. Synthetic fixture tests
  still use deterministic keypoint arrays so confidence and projection behavior
  remain stable in CI.
- Real appliance photos must be added under `data/templates/` before a public
  demo with actual camera images.
