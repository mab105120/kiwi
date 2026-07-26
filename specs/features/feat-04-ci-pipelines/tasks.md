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
- [x] Push a scratch commit with a deliberately failing lint rule, unit test,
  contract test, and coverage drop (one at a time or together) to confirm
  each surfaces as its own distinctly-named, attributable job failure; revert
  the scratch commit once confirmed (confirmed in GH Actions run 30174793949:
  `lint`, `test (libs/platform_common)`, `contract-test (identity)`, and
  `backend-coverage` each failed independently on their own step while all
  other legs stayed green; `docker-build (identity)` also failed in that run
  but from an unrelated transient Docker Hub network timeout, confirmed by a
  clean pass on retry. Reverted in commit 83ceb57, verified green again in
  run 30174947211.)

## Frontend CI

- [x] Add `.github/workflows/frontend-ci.yml` triggered on `push` (all
  branches) and `pull_request` (against `main`)
- [x] `install-and-lint` job: `npm --prefix frontend ci && npm --prefix
  frontend run lint`
- [x] `test` job: `npm --prefix frontend run test -- --coverage`
- [x] Push a scratch commit with a deliberately failing lint rule, test, and
  coverage drop to confirm each fails its own job distinctly; revert once
  confirmed (confirmed across GH Actions runs 30175811332 and 30175898326:
  `install-and-lint` failed independently on two unused-variable errors in
  both runs; `test` failed on the broken assertion in the first run, then
  — after fixing the assertion but keeping the uncovered helper in a
  follow-up scratch commit — failed independently on the coverage threshold
  (16.66% vs the configured 50% floor) in the second run. Frontend's coverage
  threshold is 50%, not the 80% this task group originally said, per a
  `// TODO: raise to 80%` already in `vite.config.js` — pre-existing gap, not
  introduced here. Both scratch commits reverted in 775cf25/8aa6e8c, verified
  green again in run 30175976212.)

## Infra CI

- [x] Add `.github/workflows/infra-ci.yml` triggered on `push` (all branches)
  and `pull_request` (against `main`)
- [x] `synth` job: `cd infra && uv sync && npm install -g aws-cdk && uv run
  cdk synth`, with no AWS credentials configured on the runner
- [x] Confirm the job passes with no credentials present (validates that
  `network_stack.py`/`data_stack.py` still contain no `from_lookup`-style
  live-AWS construct; confirmed in GH Actions run 30176178117 on a
  GitHub-hosted runner with no AWS credentials configured)
- [x] Push a scratch commit with a deliberately broken stack (e.g. a syntax
  error) to confirm `synth` fails distinctly; revert once confirmed
  (confirmed in run 30176249219: a missing `:` in `network_stack.py`'s
  `NetworkStack.__init__` signature failed `synth` with a `SyntaxError`;
  reverted in commit 043ec3a, verified green again in run 30176290811)

## Secret scanning

- [x] Add `.github/workflows/secret-scan.yml` triggered on `push` (all
  branches) and `pull_request` (against `main`), running
  `gitleaks/gitleaks-action` — **revised from the original plan.md design
  during implementation**: `gitleaks/gitleaks-action` hardcodes diff-only
  scanning on `push`/`pull_request` events (single commit, or the pushed
  commit range) and only scans full history on `workflow_dispatch`/`schedule`
  triggers — confirmed by reading the action's source
  (github.com/gitleaks/gitleaks-action, `dist/index.js`'s `Scan()`/`start()`
  functions). Forcing a full-history scan on every push/PR isn't structurally
  supported by the action without dropping to the bare `gitleaks` CLI, and
  isn't actually needed: every commit lands via this same push/PR path going
  forward, so diff-only scanning already covers all new commits. The repo is
  new with no pre-existing secrets, so the one remaining gap a full-history
  scan would close (pre-CI history never having been scanned) doesn't apply
  here — skipping the manual one-time baseline scan below for that reason.
- [x] ~~Run it once against the current repo state; if it flags an existing
  false positive, add a scoped `.gitleaks.toml` allowlist entry (not a
  broader suppression)~~ Skipped: repo is new and confirmed to have no
  pre-existing secrets (owner's call), so no baseline scan was run and no
  `.gitleaks.toml` was needed.
- [x] Push a scratch commit containing a realistic-looking fake credential to
  confirm the job fails distinctly; revert once confirmed (first attempt in
  run 30176462925 used AWS's own canonical example key,
  `AKIAIOSFODNN7EXAMPLE`, which passed silently — gitleaks's default
  ruleset allowlists it by design because it contains "EXAMPLE". Retried
  with a realistic fake GitHub PAT (`ghp_...`), which correctly failed the
  `gitleaks` job distinctly in run 30176736235. Both scratch commits
  reverted in 5c694be/efc5b4c, verified green again in run 30176778287.)

## Verification & wrap-up

- [x] Open a PR containing all four workflow files and confirm every job
  listed above appears and passes on a clean commit
- [x] Configure required-status-check branch protection on `main` covering
  every job introduced by this feature (repo settings / `gh api` /
  `gh ruleset` — not a file committed to the repo; only possible once each
  job has run at least once against `main`)
- [x] Update this feature's `spec.md`/`plan.md` if anything changed during
  implementation (constitution W-1) — updated in commit 670a420: frontend
  coverage threshold is 50%, not 80% (`plan.md`'s frontend-ci section and
  Risks; `spec.md`'s scope/acceptance criteria), and secret scanning is
  diff-only per push/PR, not full repository history (`plan.md`'s
  secret-scan section, Risks, and Sequencing step 5; `spec.md`'s scope). The
  backend-coverage per-package-vs-combined deviation was already recorded in
  `plan.md` from the start (not something introduced after the fact), so no
  further edit was needed there.
- [x] Check off the `feat-04-ci-pipelines` line in
  `specs/phases/roadmap.md`'s Phase 0 feature breakdown
