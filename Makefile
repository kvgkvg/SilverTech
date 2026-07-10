.PHONY: setup-api seed-api run-api test-api test-vision test-label test smoke

setup-api:
	python3 -m pip install -e apps/api

# button_offsets lives outside the seed data: without it every /api/vision/logo-anchor
# call fails with 409 "no template has logo_bbox + button_offsets + image".
seed-api:
	PYTHONPATH=apps/api python3 -m app.storage.seed
	PYTHONPATH=apps/vision-tools python3 apps/vision-tools/scripts/compute_logo_offsets.py

run-api:
	PYTHONPATH=apps/api uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

test-api:
	PYTHONPATH=apps/api pytest -q apps/api/tests tests/contract

test-vision:
	PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests

test-label:
	PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests/test_label_geometry.py \
	  apps/vision-tools/tests/test_label_gemini_client.py \
	  apps/vision-tools/tests/test_label_extract.py \
	  apps/vision-tools/tests/test_label_detect.py \
	  apps/vision-tools/tests/test_label_describe.py \
	  apps/vision-tools/tests/test_label_qc.py \
	  apps/vision-tools/tests/test_label_pipeline.py \
	  apps/vision-tools/tests/test_label_eval_detect.py

test: test-api test-vision

smoke: seed-api
	PYTHONPATH=apps/api pytest -q apps/api/tests/test_query_flow.py apps/api/tests/test_invalid_button_id_handling.py
