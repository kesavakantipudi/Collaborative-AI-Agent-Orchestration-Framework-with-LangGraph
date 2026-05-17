up:
	docker compose up --build -d

down:
	docker compose down --volumes

test:
	python scripts/run_integration_test.py

ci:
	docker compose up --build -d
	python scripts/run_integration_test.py
	docker compose down --volumes
