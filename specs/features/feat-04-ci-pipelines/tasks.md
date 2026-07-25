# Tasks: CI Pipelines

Six groups below, each intended as its own commit, in order: Coverage
tooling → Backend CI → Frontend CI → Infra CI → Secret scanning →
Verification & wrap-up. Branch protection is a repo-settings change, not a
commit, so it's called out separately at the end.

## Coverage tooling

- [x] Add `pytest-cov` to `backend/pyproject.toml`'s `dev` dependency group;
  `uv lock` and `uv sync` to pick it up
- [x] Add `@vitest/coverage-v8` to `frontend/package.json`'s
  `devDependencies`; `npm install` to pick it up
- [x] Configure an 80% statements/lines coverage threshold in
  `frontend/vite.config.js`'s `test.coverage.thresholds` (vitest's `v8`
  provider)
- [x] Verify locally: `npm --prefix frontend run test -- --coverage` reports
  coverage and enforces the threshold

## Backend CI

- [x] Add `.github/workflows/backend-ci.yml` triggered on `push` (all
  branches) and `pull_request` (against `main`)
- [x] `lint` job: `cd backend && uv sync --all-packages && uv run ruff check
  . && uv run mypy .` (matches `make lint-backend` unchanged, one job for the
  whole workspace)
- [x] `test` job, matrixed over `libs/platform_common`, `services/identity`,
  `services/app-api`, `services/worker`: `uv run pytest <package-path>
  --ignore=<package-path>/tests/contract` (no `--cov` here — see below;
  revised from the original plan.md design during implementation)
- [x] `contract-test` job, matrixed over `services/identity`,
  `services/app-api`, `services/worker`: `uv run pytest
  services/<service>/tests/contract`
- [x] `backend-coverage` job, **not matrixed** (single job across all four
  packages combined): `uv run pytest libs/platform_common services/identity
  services/app-api services/worker --cov=libs/platform_common
  --cov=services/identity/app --cov=services/app-api/app
  --cov=services/worker/app --cov-fail-under=80` — identical to the
  Makefile's `test-backend` target. Added because `identity`/`app-api`/
  `worker` have no unit tests yet (only empty `tests/unit/__init__.py`
  placeholders), so a *per-package* `--cov-fail-under=80` as originally
  planned would fail immediately at 0% for each of those three, even though
  combined backend coverage is 87% today. This also aligns with plan.md's own
  Risks section, which already called for one coverage number per language,
  not per service — the per-package matrix design in the original `test` job
  description contradicted that. Consequence: the check enforces 80% across
  the backend as a whole, not per-service; a service can sit at 0% coverage
  indefinitely as long as the combined number holds.
- [x] `docker-build` job, matrixed over `identity`, `app-api`, `worker`: reuse
  the existing `make build-<service>` targets unchanged
- [x] Verify the `test`/`--ignore` split and the `contract-test` job together
  cover exactly the same files `make test-backend` runs today — nothing
  silently dropped between the two jobs (confirmed via `pytest
  --collect-only`: both collect the same 14 `platform_common` tests and 0
  contract tests, matching `make test-backend`'s full collection exactly)
- [ ] Push a scratch commit with a deliberately failing lint rule, unit test,
  contract test, and coverage drop (one at a time or together) to confirm
  each surfaces as its own distinctly-named, attributable job failure; revert
  the scratch commit once confirmed

## Frontend CI

- [ ] Add `.github/workflows/frontend-ci.yml` triggered on `push` (all
  branches) and `pull_request` (against `main`)
- [ ] `install-and-lint` job: `npm --prefix frontend ci && npm --prefix
  frontend run lint`
- [ ] `test` job: `npm --prefix frontend run test -- --coverage`
- [ ] Push a scratch commit with a deliberately failing lint rule, test, and
  coverage drop to confirm each fails its own job distinctly; revert once
  confirmed

## Infra CI

- [ ] Add `.github/workflows/infra-ci.yml` triggered on `push` (all branches)
  and `pull_request` (against `main`)
- [ ] `synth` job: `cd infra && uv sync && npm install -g aws-cdk && uv run
  cdk synth`, with no AWS credentials configured on the runner
- [ ] Confirm the job passes with no credentials present (validates that
  `network_stack.py`/`data_stack.py` still contain no `from_lookup`-style
  live-AWS construct)
- [ ] Push a scratch commit with a deliberately broken stack (e.g. a syntax
  error) to confirm `synth` fails distinctly; revert once confirmed

## Secret scanning

- [ ] Add `.github/workflows/secret-scan.yml` triggered on `push` (all
  branches) and `pull_request` (against `main`), running
  `gitleaks/gitleaks-action` against full repository history (not diff-only)
- [ ] Run it once against the current repo state; if it flags an existing
  false positive, add a scoped `.gitleaks.toml` allowlist entry (not a
  broader suppression)
- [ ] Push a scratch commit containing a realistic-looking fake credential to
  confirm the job fails distinctly; revert once confirmed

## Verification & wrap-up

- [ ] Open a PR containing all four workflow files and confirm every job
  listed above appears and passes on a clean commit
- [ ] Configure required-status-check branch protection on `main` covering
  every job introduced by this feature (repo settings / `gh api` /
  `gh ruleset` — not a file committed to the repo; only possible once each
  job has run at least once against `main`)
- [ ] Update this feature's `spec.md`/`plan.md` if anything changed during
  implementation (constitution W-1)
- [ ] Check off the `feat-04-ci-pipelines` line in
  `specs/phases/roadmap.md`'s Phase 0 feature breakdown
