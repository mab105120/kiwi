.PHONY: install lint test install-backend lint-backend test-backend \
	install-frontend lint-frontend test-frontend \
	up down client build-identity build-app-api build-worker

install: install-backend install-frontend

lint: lint-backend lint-frontend

test: test-backend test-frontend

install-backend:
	cd backend && uv sync --all-packages

lint-backend:
	cd backend && uv run ruff check . && uv run mypy .

test-backend:
	cd backend && uv run pytest libs/platform_common services/identity services/app-api services/worker \
		--cov=libs/platform_common --cov=services/identity/app --cov=services/app-api/app --cov=services/worker/app \
		--cov-fail-under=80; status=$$?; [ $$status -eq 0 ] || [ $$status -eq 5 ]

install-frontend:
	npm --prefix frontend install

lint-frontend:
	npm --prefix frontend run lint

test-frontend:
	npm --prefix frontend run test -- --coverage

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
