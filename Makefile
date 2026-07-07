.PHONY: install lint test install-backend lint-backend test-backend \
	up down client build-identity build-app-api build-worker

install: install-backend
	# TODO: call install-frontend once it exists

lint: lint-backend
	# TODO: call lint-frontend once it exists

test: test-backend
	# TODO: call test-frontend once it exists

install-backend:
	cd backend && uv sync --all-packages

lint-backend:
	cd backend && uv run ruff check . && uv run mypy .

test-backend:
	cd backend && uv run pytest services/identity services/app-api services/worker; status=$$?; [ $$status -eq 0 ] || [ $$status -eq 5 ]

up:
	docker-compose up -d

down:
	docker-compose down

build-identity:
	docker build -f backend/services/identity/Dockerfile -t identity backend/

build-app-api:
	docker build -f backend/services/app-api/Dockerfile -t app-api backend/

build-worker:
	docker build -f backend/services/worker/Dockerfile -t worker backend/

client:
	# TODO: generate frontend/src/api clients from contracts/*.openapi.yaml
	@echo "TODO: generate client"
