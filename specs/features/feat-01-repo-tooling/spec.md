# Spec: Repo Tooling

## Why

Phase 0 (`specs/phases/roadmap.md`) needs a working local dev loop before any
other Phase 0 feature can be built or verified. Right now `make install`,
`make lint`, and `make test` are `TODO: echo` stubs, and `frontend/` has no
app at all (only its `CLAUDE.md`). Nobody can install dependencies, lint, or
run a test for any service without this landing first.

## Scope

- Backend: `make install` runs `uv sync` across the workspace declared in
  `backend/pyproject.toml` (already lists `libs/platform_common` +
  the three services as members).
- Backend: `make lint` runs ruff + mypy across the workspace.
- Backend: `make test` runs pytest per service (`identity`, `app-api`,
  `worker`), including the already-scaffolded `tests/unit` and
  `tests/contract` directories.
- Frontend: scaffold a minimal Vite + React + JavaScript app under
  `frontend/` (per `frontend/CLAUDE.md`'s described layout:
  `src/api`, `src/components`, `src/routes`, `src/lib`, `src/features`),
  with working `install`, `lint` (eslint), and `test` (vitest) scripts.
- `make install`/`make lint`/`make test` each run both backend and frontend
  steps; `make install-backend`/`install-frontend`,
  `make lint-backend`/`lint-frontend`, and `make test-backend`/`test-frontend`
  are also available to run just one side.
- `make up` / `make down` already work (docker-compose for MySQL +
  LocalStack) — out of scope, no change needed.

## Out of scope

- CI workflow changes (`feat-04-ci-pipelines` — this feature only needs to
  make the commands work locally; wiring them into GitHub Actions is a
  separate feature since it depends on this one).
- Any actual service business logic, routes, or migrations.
- `platform_common` implementation content (`feat-02-platform-common-lib`).
- Docker image builds (`make build-*` already works and is unrelated to
  install/lint/test).

## Acceptance criteria

- [ ] `make install` on a clean checkout installs all backend + frontend
  dependencies with no manual steps; `make install-backend` and
  `make install-frontend` each work standalone too.
- [ ] `make lint` runs ruff + mypy on all backend packages and eslint on
  the frontend, and exits non-zero on a deliberately introduced lint error;
  `make lint-backend` and `make lint-frontend` each work standalone and
  scope to only their side.
- [ ] `make test` runs pytest for each of the three backend services and
  vitest for the frontend, and exits non-zero on a deliberately failing
  test; `make test-backend` and `make test-frontend` each work standalone
  and scope to only their side.
- [ ] Frontend scaffold builds (`vite build`) and serves a blank page
  locally.
- [ ] No secrets or credentials introduced anywhere in this change
  (constitution T-4).
