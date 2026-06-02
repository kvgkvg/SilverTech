# Quickstart: SilverTech Camera Voice Guidance

## Prerequisites

- Flutter 3.x and Android SDK for mobile MVP.
- Python 3.12 for the FastAPI backend and vision tooling.
- OpenCV available for offline tools and mobile native module integration.
- SQLite for MVP local storage.
- STT and LLM provider credentials configured in local environment variables.

## 1. Seed MVP Templates

1. Add 2-3 real appliance panel images under `data/templates/`.
2. Create device/template/button seed records with reviewed `official` status.
3. Store each button with a stable `button_id`, Vietnamese name, function
   description, and template-coordinate bounding box or polygon.
4. Precompute feature descriptors into `data/descriptors/` where supported.

## 2. Verify Offline Matching

1. Place test camera images under `data/test-images/`.
2. Run the offline matcher against each image.
3. Confirm the selected template is correct under normal lighting.
4. Confirm projected button boxes overlap manually labeled ground truth.
5. Confirm low-light, glare, blurred, partial, wrong-brand, and unsupported
   images return a friendly failure instead of accepted guidance.

## 3. Run Backend MVP

1. Start the API service with the SQLite database.
2. Verify `GET /api/templates/{id}` returns official templates and buttons.
3. Verify `POST /api/vision/candidates` returns candidates by brand/appliance
   type.
4. Verify `POST /api/query` rejects any generated step whose `button_id` is not
   present in the selected template.
5. Verify `POST /api/stt` returns Vietnamese text or a typed-input recovery
   instruction.

## 4. Run Mobile MVP

1. Launch the Flutter app on a low-to-mid-range Android test phone.
2. Open `CameraScreen`; it should show a simple Vietnamese instruction to point
   the camera at the control panel.
3. Scan a supported panel; the app should retrieve candidate templates, match
   the live view, and show no highlight until confidence passes.
4. Ask a Vietnamese task question.
5. Confirm the app displays one large-text Vietnamese step at a time and
   highlights only the validated button for that step.
6. Move the phone or obscure the panel; the app should stop highlighting and ask
   the user to rescan.

## 5. Validate Review Flow

1. Submit a new panel image and proposed button labels.
2. Confirm the submission remains `pending` and is not used as official runtime
   guidance.
3. Accept, edit, or reject the submission through the admin review endpoint.
4. Confirm only accepted templates become official and versioned.

## Acceptance Test Checklist

- Known template under normal lighting selects the correct template.
- Projected button boxes overlap ground truth for accepted matches.
- Vietnamese query returns validated steps using only known `button_id` values.
- Low confidence produces rescan/manual-selection guidance, not a highlight.
- One elderly or elderly-like user completes at least one supported appliance
  task using camera guidance.
