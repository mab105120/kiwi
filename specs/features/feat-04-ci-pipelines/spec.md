# Spec: CI Pipelines

## Why

Phase 0 (`specs/phases/roadmap.md`) requires CI that blocks merges on failing
contract tests, lint, or type checks (constitution Q-2) — "CI running contract
tests, lint, and type checks" is called out explicitly in the phase's stated
goal. Right now there is no CI at all: no `.github/workflows/` directory
exists anywhere in this repo. `feat-01-repo-tooling` already gave every
service and the frontend real local `make`/`npm` targets (`lint`, `test`,
`install`), and `feat-02-platform-common-lib` gave the backend something
substantive to actually lint and test. Those local checks only protect the
repo if something runs them automatically on every change and stops bad code
from merging — otherwise Q-2 is aspirational.

This feature closes that gap: it makes the checks that already exist locally
run automatically for every push/PR, for all three backend services, the
frontend, and `infra/` — and adds the two Q-2 checks that don't exist in any
form yet (coverage threshold, secret scanning).

## Scope

- **A CI workflow covering each of the three backend services**
  (`identity`, `app-api`, `worker`) and `platform_common`: on every push/PR,
  automatically lint, type-check, run unit tests, run that service's contract
  tests against its `contracts/` OpenAPI document, and build its Docker image,
  using the same commands a developer already runs locally via the `Makefile`
  (`feat-01-repo-tooling`).
- **A CI workflow covering the frontend**: on every push/PR, automatically
  install dependencies, lint, and run the test suite, mirroring the frontend's
  local `npm` scripts.
- **A CI workflow covering `infra/`**: on every push/PR, automatically
  validate that the CDK app synthesizes cleanly (`feat-03-infra-network-data`'s
  `NetworkStack`/`DataStack`), using no AWS credentials — a static
  well-formedness check, not a deploy or a diff against any live environment.
- **A repo-wide test-coverage threshold**, enforced in CI for the backend and
  frontend test suites introduced by `feat-01`/`feat-02`: a pull request whose
  change drops coverage below that threshold fails its check, the same as a
  failing test would. Backend enforces 80%. Frontend enforces 50% for now
  (revised during implementation — see `plan.md`), with a `TODO` in
  `vite.config.js` to raise it to 80% once more frontend code/tests land.
- **A secret-scanning check**, run on every push/PR (revised during
  implementation to diff-only rather than full repository history each run —
  see `plan.md`), so a credential or key committed in any of those commits
  fails the build. (Tool choice: Gitleaks — decided during this conversation,
  to be recorded in `plan.md`.)
- Every workflow above runs for every push and every pull request against
  `main` — contributors get the same signal whether they're pushing to a
  branch or opening a PR.
- A pull request cannot be merged while any of these checks are failing
  (constitution Q-2) — required-status-check protection on `main` covering
  every job introduced by this feature.
- Failures are attributable: a broken lint rule, a failing test, a failing
  contract test, a failed Docker build, a coverage drop, a failed `cdk synth`,
  or a detected secret must each be identifiable as its own distinct,
  clearly-named check, not bundled into one opaque job.

## Out of scope

- **Deploying anything**, from any workflow, including `infra/`'s. No image
  push to a registry, no `cdk deploy`, no environment credentials or AWS OIDC
  role usage anywhere in this feature. That's `feat-07-deploy-pipeline`,
  which is explicitly the feature that wires CI (this feature) together with
  CD, including instantiating `stacks/cicd_stack.py`.
- **`cdk diff` against a live environment, or any other check that requires
  AWS credentials.** The `infra/` workflow added by this feature only proves
  the app synthesizes; comparing it against deployed state is a CD-adjacent
  concern for `feat-07-deploy-pipeline`.
- **New tests, new lint rules, or fixes to existing lint/type/test failures**
  beyond what's needed to meet the coverage thresholds above. This feature makes
  existing local checks (plus coverage and secret-scanning) run in CI; it does
  not otherwise change what those checks check. If something newly starts
  failing in CI that passes locally, that's a bug to fix as part of this
  feature, but expanding check coverage further than specified above is not
  this feature's job.
- **Remediating any secret the scanning tool finds**, or rewriting git history
  to remove one. If the scan turns up a real finding, that's handled as its
  own incident, not folded into this feature's rollout.

## Acceptance criteria

- [ ] Opening a pull request against `main` automatically runs lint, type
  checks, unit tests, contract tests, and a Docker build for each of
  `identity`, `app-api`, and `worker`; lint + tests for the frontend; and a
  `cdk synth` check for `infra/` — with no manual trigger required.
- [ ] Pushing a commit to any branch runs the same checks as opening a PR
  would, so failures are visible before a PR is even opened.
- [ ] A pull request with a failing lint, type-check, unit test, or contract
  test in any one service, a failing `infra/` synth, a coverage drop below
  the backend's 80% or the frontend's 50% threshold, or a detected secret
  cannot be merged into `main`, and the failing check is identifiable by name
  as belonging to that specific service/check type.
- [ ] A pull request where every check passes is mergeable with no additional
  manual approval step beyond what the repo already requires.
- [ ] None of the new workflows require or reference AWS credentials, or any
  deploy target — including the `infra/` workflow, which only synthesizes.
- [ ] A pull request that drops backend test coverage below 80%, or frontend
  test coverage below 50%, fails its coverage check even if every individual
  test still passes.
- [ ] A pull request that introduces a committed secret (e.g. a test fixture
  containing a realistic-looking API key) fails the secret-scanning check.
- [ ] Running the equivalent `make`/`npm`/`cdk synth` commands locally
  produces the same pass/fail result as the corresponding CI check, for a
  change that is known to pass and a change that is known to fail.
