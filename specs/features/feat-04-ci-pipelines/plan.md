# Plan: CI Pipelines

## Approach

Four independent GitHub Actions workflow files under `.github/workflows/`,
each scoped to one part of the repo, all triggered on `push` (any branch) and
`pull_request` (against `main`), all using only `ubuntu-latest` runners (cost
is a non-issue on this public repo, but there's no reason to reach for a
pricier runner either). No workflow in this feature touches AWS — that
starts in `feat-07-deploy-pipeline`. Each job is named so it reads
unambiguously as a required status check (e.g. `backend-test (identity)`,
`docker-build (worker)`), per the spec's "failures are attributable"
requirement.

**1. `.github/workflows/backend-ci.yml`**

- `lint` — one job, not per-service: `cd backend && uv sync --all-packages &&
  uv run ruff check . && uv run mypy .`, matching `make lint-backend`
  unchanged. Kept as a single job because the Makefile already lints/type-
  checks the whole `backend/` workspace in one pass (`ruff`/`mypy` configured
  at the workspace root in `backend/pyproject.toml`) — splitting it
  per-service would mean inventing per-service lint config that doesn't
  exist today, out of proportion to this feature.
- `test` — matrix over the four backend packages (`libs/platform_common`,
  `services/identity`, `services/app-api`, `services/worker`), each running
  `uv run pytest <package-path> --ignore=<package-path>/tests/contract`, no
  `--cov` flag. Excluding `tests/contract` here is what makes the next job's
  contract results attributable separately rather than double-counted
  silently inside "test".
- `backend-coverage` — **revised during implementation from the original
  per-package `--cov-fail-under=80` on the `test` matrix above.** A single,
  non-matrixed job running `uv run pytest libs/platform_common
  services/identity services/app-api services/worker --cov=libs/platform_common
  --cov=services/identity/app --cov=services/app-api/app
  --cov=services/worker/app --cov-fail-under=80` — identical to the
  Makefile's `test-backend` target. The original per-package design was
  found to fail immediately for `identity`/`app-api`/`worker` (0% coverage
  each, since those services only have empty `tests/unit/__init__.py`
  placeholders today) even though combined backend coverage is 87%. It also
  contradicted this plan's own Risk note below, which already called for one
  coverage number per language rather than per service. Requires adding
  `pytest-cov` to `backend/pyproject.toml`'s `dev` dependency group (not
  present today). The Makefile's `test-backend` target also now carries
  `--cov=<paths> --cov-fail-under=80` (all four packages, one invocation) —
  added so `make test-backend` fails on a coverage drop exactly as this job
  would, per spec.md's local/CI parity acceptance criterion. It does not also
  split out `--ignore=tests/contract`/a separate contract run locally, since
  that split exists in CI purely for failure attribution, not for pass/fail
  parity — a failing contract test already fails `make test-backend` today.
  Consequence of the combined-coverage design: the check enforces 80% across
  the backend as a whole, not per service — a service can sit at 0% coverage
  indefinitely as long as the aggregate holds.
- `contract-test` — matrix over the three services with a contract suite
  (`identity`, `app-api`, `worker`; `platform_common` has none), each running
  `uv run pytest services/<service>/tests/contract`. This is new: today
  `make test-backend` runs one `pytest` invocation across all four packages
  with no contract/unit split, so a contract failure and a unit failure are
  currently indistinguishable. Splitting this out is necessary to meet the
  spec's per-check attributability requirement, and only affects CI wiring —
  `make test-backend` itself is untouched, so local dev workflow doesn't
  change.
- `docker-build` — matrix over the three services with a Dockerfile
  (`identity`, `app-api`, `worker`), each running the existing `make
  build-<service>` target unchanged (`docker build -f
  backend/services/<service>/Dockerfile -t <service> backend/`).

**2. `.github/workflows/frontend-ci.yml`**

- `install-and-lint` — `npm --prefix frontend ci && npm --prefix frontend run
  lint`.
- `test` — `npm --prefix frontend run test -- --coverage`, with a coverage
  threshold of 80% (statements/lines) configured in `vite.config.js`'s
  `test.coverage.thresholds` (vitest's built-in `v8` coverage provider, which
  fails the run itself when a threshold isn't met — no separate CI-side
  check needed). Requires adding `@vitest/coverage-v8` as a frontend dev
  dependency (not present today). The Makefile's `test-frontend` target now
  runs `npm --prefix frontend run test -- --coverage` too (previously plain
  `npm run test`), for the same local/CI parity reason as the backend `test`
  job above.

**3. `.github/workflows/infra-ci.yml`**

- `synth` — `cd infra && uv sync && npm install -g aws-cdk && uv run cdk
  synth`. Confirmed safe to run with no AWS credentials: neither
  `network_stack.py` nor `data_stack.py` uses any `from_lookup`-style
  construct that would make CDK call the AWS API during synth (verified by
  inspection) — synth is a pure, static render of `cdk.json`'s committed
  context into CloudFormation templates. If a future change introduces a
  lookup construct, this job would start failing in CI for lack of
  credentials, which is the correct signal (a synth that needs live AWS state
  needs `feat-07`'s deploy-role wiring, not a workaround here).
- No `lint`/`mypy` job for `infra/` in this workflow: `infra/pyproject.toml`
  has no `ruff`/`mypy` dev dependencies configured today (unlike `backend/`),
  and adding lint tooling to `infra/` is a tooling decision outside this
  feature's scope (CI pipelines wire up checks that exist; they don't invent
  new ones for a package that doesn't have them, matching this feature's own
  "out of scope: new lint rules" boundary).

**4. `.github/workflows/secret-scan.yml`**

- Single job running `gitleaks/gitleaks-action` (the tool decided on in
  spec.md discussion) against the full repository history on every push and
  PR — not a diff-only scan, so a secret introduced in any earlier commit on
  a branch is caught even if a later commit only touches unrelated files.
  No config file is added beyond the workflow itself unless gitleaks' default
  ruleset produces false positives against this repo once it's run for real,
  in which case a `.gitleaks.toml` allowlist is added at that point — not
  speculatively now.

**5. Branch protection**

- Add every job introduced above as a required status check on `main` in the
  repo's branch protection settings. This is a GitHub repo-settings change
  (via the web UI or `gh api`/`gh ruleset`), not a file committed to the
  repo, and has to happen once all four workflows have run at least once
  (GitHub only lists a check as available to require after it's executed at
  least once on the target branch) — so this is necessarily the last step,
  done after the workflows are merged and have run.

## Risks

- **Splitting backend contract tests out of `make test-backend`'s existing
  single pytest invocation is new surface, not a pure lift-and-shift of an
  existing command** (unlike, e.g., the docker-build jobs, which just reuse
  `make build-<service>` verbatim). Worth double-checking during
  implementation that `--ignore=<path>/tests/contract` on the `test` job and
  the explicit `contract-test` job together cover exactly the same set of
  test files `make test-backend` runs today — no test should silently stop
  running in CI because it fell in the gap between the two jobs.
- **Coverage is enforced as two separate thresholds (backend, frontend), not
  one merged repo-wide number.** Python (`pytest-cov`) and JS (`vitest`/`v8`)
  coverage tools don't produce a mergeable combined metric without an
  external service (e.g. Codecov), which would be a new third-party
  dependency this feature doesn't otherwise need. Two 80% checks — one per
  language — satisfies the spirit of "repo-wide 80%" without that dependency.
  Flagging this explicitly since spec.md's "repo-wide" phrasing could be read
  as requiring one merged number.
- **`cdk synth` needing no AWS credentials is a real assumption, not just a
  simplification** — confirmed by inspection today, but if a later change to
  `network_stack.py`/`data_stack.py` (e.g. importing an existing resource by
  ARN/lookup) introduces a live AWS API call during synth, this job starts
  failing in CI with no credentials configured. That's the correct failure
  mode (surfaces the problem immediately) rather than something to silently
  work around by adding credentials to this workflow.
- **Gitleaks scanning full history on every run**, rather than only the
  commits in a push/PR, is slower as the repo grows but catches secrets
  introduced in earlier commits on a branch that a diff-only scan would miss
  entirely. Acceptable trade at the repo's current size; revisit if scan time
  becomes noticeable.
- **Required-status-check configuration lives in GitHub repo settings, not
  in a file this feature commits** — it isn't reviewable in the same PR as
  the workflow YAML, and someone needs repo-admin access to apply it. Calling
  this out so it isn't missed as an implicit "the YAML alone is done" step.

## Sequencing

1. Add `pytest-cov` to `backend/pyproject.toml`'s dev group and
   `@vitest/coverage-v8` to `frontend/package.json`'s devDependencies; wire
   the 80% threshold into the frontend's `vite.config.js` and the backend
   `test` job's `--cov-fail-under=80` flag.
2. Write `.github/workflows/backend-ci.yml` (`lint`, `test` matrix,
   `contract-test` matrix, `docker-build` matrix); verify each job locally
   first via the equivalent `uv run`/`make` command before trusting the CI
   run.
3. Write `.github/workflows/frontend-ci.yml` (`install-and-lint`, `test` with
   coverage).
4. Write `.github/workflows/infra-ci.yml` (`synth`); confirm it runs with no
   AWS credentials configured on the runner.
5. Write `.github/workflows/secret-scan.yml` (gitleaks, full history); run it
   once against the current repo state and resolve any finding (or add a
   scoped allowlist) before merging.
6. Open a PR with all four workflow files, confirm every job listed above
   appears and passes (and that a deliberately broken test/lint/coverage/
   secret on a scratch commit makes the corresponding job fail, to prove
   attribution works), then configure required-status-check branch
   protection on `main` covering every job.
