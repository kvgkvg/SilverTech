# Demo Script

1. Run `make seed-api`.
2. Run `make run-api`.
3. Open `http://127.0.0.1:8000/docs`.
4. Call `POST /api/vision/candidates` with brand `Toshiba` and appliance type
   `washing_machine`.
5. Call `GET /api/templates/template_toshiba_washer_panel_v1`.
6. Call `POST /api/query` with `Lam sao de giat nhanh?`.
7. Show that the returned step uses `button_id=quick_wash`.
8. Run `make test-vision` to show low-confidence rejection and projection tests.
