# Backend API

Canonical contract: `specs/001-camera-voice-guidance/contracts/openapi.yaml`.

Implemented MVP endpoints:

- `POST /api/vision/candidates`
- `GET /api/templates/{template_id}`
- `POST /api/stt`
- `POST /api/query`
- `POST /api/vision/logs`
- `POST /api/submissions`
- `POST /api/admin/submissions/{submission_id}/review`

Errors return Vietnamese recovery guidance with a `recovery_action`.
