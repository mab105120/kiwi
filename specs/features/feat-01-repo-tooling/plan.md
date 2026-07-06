# Plan: Repo Tooling

## Approach

Backend and frontend tracks are independent and can be built in either
order; sequencing below does backend first since more scaffolding already
exists there (workspace `pyproject.toml`, per-service directories).

**Backend**

- Add ruff + mypy as dev dependencies at the workspace root
  (`backend/pyproject.toml`), configured to run across all workspace
  members.
- `make install-backend` → `cd backend && uv sync --all-packages` (or
  equivalent workspace-wide sync).
- `make lint-backend` → `uv run ruff check backend` + `uv run mypy` per
  service (mypy generally needs per-package invocation rather than a
  single workspace-wide run).
- `make test-backend` → loop `uv run --package <service> pytest` for
  `identity`, `app-api`, `worker`, and `platform_common`. Each service's
  `tests/unit` and `tests/contract` dirs already exist (currently just
  `__init__.py`), so pytest should run and report "0 tests collected"
  cleanly until later features add real tests.

**Frontend**

- Scaffold with `npm create vite@latest -- --template react`, then
  reshape into the layout `frontend/CLAUDE.md` already documents
  (`src/api`, `src/components`, `src/routes`, `src/lib`, `src/features`).
- Add eslint + vitest config.
- `make install-frontend`/`lint-frontend`/`test-frontend` → corresponding
  `npm --prefix frontend <cmd>` calls.
- `make install`/`lint`/`test` become thin umbrella targets that each call
  their `-backend` and `-frontend` counterparts, so both the combined and
  per-side commands work.

## Risks

- mypy across a `uv` workspace with path-dependency packages
  (`platform-common` referenced via `tool.uv.sources` in each service's
  `pyproject.toml`) can be fiddly to get resolving cleanly — may need a
  per-service mypy invocation rather than one root config. Budget time to
  verify this rather than assuming a single command works.
- Vite/React scaffolding defaults don't match `frontend/CLAUDE.md`'s
  described `src/` layout — plan to scaffold then manually reshape, not
  expect the generator to produce it.
- Nothing here touches `contracts/`, so no contract-test risk for this
  feature specifically.

## Sequencing

1. Backend: workspace `uv sync` wired to `make install-backend`.
2. Backend: ruff + mypy wired to `make lint-backend`.
3. Backend: pytest-per-service wired to `make test-backend`.
4. Frontend: scaffold app matching documented layout.
5. Frontend: install/lint/test scripts wired to `make install-frontend`,
   `make lint-frontend`, `make test-frontend`.
6. Wire `make install`/`lint`/`test` as umbrella targets calling both sides.
7. Verify all acceptance criteria on a clean checkout.
