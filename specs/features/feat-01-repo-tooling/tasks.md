# Tasks: Repo Tooling

## Backend

- [x] Add ruff + mypy dev dependencies to `backend/pyproject.toml`
- [ ] Wire `make install` to `uv sync` across the backend workspace
- [ ] Wire `make lint` to run ruff + mypy across backend packages
- [ ] Wire `make test` to run pytest for `identity`, `app-api`, `worker`
- [ ] Verify: clean checkout → `make install && make lint && make test`
  succeeds with zero tests collected (no test files exist yet)
- [ ] Verify: a deliberately broken lint rule / failing test makes
  `make lint` / `make test` exit non-zero, then revert the deliberate break

## Frontend

- [ ] Scaffold Vite + React + TypeScript app under `frontend/`
- [ ] Reshape into `src/{api,components,routes,lib,features}` layout per
  `frontend/CLAUDE.md`
- [ ] Add eslint config + `npm run lint` script
- [ ] Add vitest config + `npm run test` script
- [ ] Wire `make install` / `make lint` / `make test` to also run the
  frontend equivalents
- [ ] Verify: `npm run build` produces a deployable static bundle

## Wrap-up

- [ ] Update this feature's `spec.md`/`plan.md` if anything changed during
  implementation (constitution W-1)
- [ ] Check off the `feat-01-repo-tooling` line in
  `specs/phases/roadmap.md`'s Phase 0 feature breakdown
