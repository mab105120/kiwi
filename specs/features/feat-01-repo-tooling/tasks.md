# Tasks: Repo Tooling

## Backend

- [x] Add ruff + mypy dev dependencies to `backend/pyproject.toml`
- [x] Wire `make install-backend` to `uv sync` across the backend workspace
- [x] Wire `make lint-backend` to run ruff + mypy across backend packages
- [x] Wire `make test-backend` to run pytest for `identity`, `app-api`, `worker`
- [x] Wire umbrella `make install`/`lint`/`test` to call their
  `-backend` counterparts
- [x] Verify: clean checkout → `make install && make lint && make test`
  succeeds with zero tests collected (no test files exist yet)
- [x] Verify: a deliberately broken lint rule / failing test makes
  `make lint` / `make test` exit non-zero, then revert the deliberate break

## Frontend

- [x] Scaffold Vite + React + JavaScript app under `frontend/`
- [x] Reshape into `src/{api,components,routes,lib,features}` layout per
  `frontend/CLAUDE.md` (only `src/features/exam-authoring` scaffolded for
  now; other feature areas deferred until those features start)
- [x] Add eslint config + `npm run lint` script
- [x] Add vitest config + `npm run test` script
- [x] Wire `install-frontend`/`lint-frontend`/`test-frontend` to
  `npm --prefix frontend <cmd>` calls
- [x] Wire umbrella `make install`/`lint`/`test` to also call the
  `-frontend` counterparts (alongside the existing `-backend` calls)
- [x] Verify: `npm run build` produces a deployable static bundle

## Wrap-up

- [x] Update this feature's `spec.md`/`plan.md` if anything changed during
  implementation (constitution W-1)
- [x] Check off the `feat-01-repo-tooling` line in
  `specs/phases/roadmap.md`'s Phase 0 feature breakdown
