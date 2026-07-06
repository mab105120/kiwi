.PHONY: install lint test up down client build-identity build-app-api build-worker

install:
	# TODO: uv sync across backend workspace + npm install in frontend/
	@echo "TODO: install"

lint:
	# TODO: ruff/mypy for backend, eslint for frontend
	@echo "TODO: lint"

test:
	# TODO: pytest per backend service, vitest for frontend
	@echo "TODO: test"

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
