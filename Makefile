.PHONY: setup-api seed-api run-api test-api test-vision test smoke

setup-api:
	python3 -m pip install -e apps/api

seed-api:
	PYTHONPATH=apps/api python3 -m app.storage.seed

run-api:
	PYTHONPATH=apps/api uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

test-api:
	PYTHONPATH=apps/api pytest -q apps/api/tests tests/contract

test-vision:
	PYTHONPATH=apps/vision-tools pytest -q apps/vision-tools/tests

test: test-api test-vision

smoke:
	PYTHONPATH=apps/api python3 -m app.storage.seed
	PYTHONPATH=apps/api pytest -q apps/api/tests/test_query_flow.py apps/api/tests/test_invalid_button_id_handling.py
