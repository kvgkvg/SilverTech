# Quickstart Results

Validated on 2026-06-02.

Environment:
- Conda environment: `silvertech`
- Python: 3.12
- Dart SDK: 3.12.1
- Flutter: 3.44.1 at `/home/kvgkvg/development/flutter`
- Installed Python runtime dependencies include FastAPI, Uvicorn, SQLAlchemy,
  Alembic, Pytest, HTTPX, NumPy, PyYAML, and OpenCV.

## Passed

- `PYTHONPATH=apps/api pytest -q apps/api/tests tests/contract`
  - Result: 14 passed.
- `PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests`
  - Result: 5 passed.
- `dart run apps/mobile/test/vision/homography_projector_test.dart`
  - Result: passed.
- `dart run apps/mobile/test/guidance/instruction_player_test.dart`
  - Result: passed.
- `dart run apps/mobile/test/ui/rescan_guidance_ui_test.dart`
  - Result: passed.
- `flutter test` in `apps/mobile`
  - Result: passed.
- `PYTHONPATH=apps/api python3 -m app.storage.seed`
  - Result: seeded 3 official template records with labeled buttons.
- Backend smoke check:
  - Toshiba washing-machine candidates returned
    `template_toshiba_washer_panel_v1`.
  - Template buttons returned `dry_mode`, `quick_wash`, and `start_pause`.
  - Query `Lam sao de giat nhanh?` returned `button_id=quick_wash`.

## Pending

- Flutter doctor warns that Flutter/Dart are not on PATH and Chrome is missing
  for web development. Android toolchain is available and web is not part of the
  MVP target.
- Real appliance camera validation is pending until reviewed panel images and a
  physical Android test device are available.
