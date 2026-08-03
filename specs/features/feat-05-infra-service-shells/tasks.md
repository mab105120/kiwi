# Tasks: Infra Service Shells

Seven groups below, each intended as its own commit, in the order
`plan.md`'s Sequencing lays out: Shared services stack → Contract/route-prefix
change → Identity service stack → App-api service stack → Worker keep-alive
+ service stack → Docs → Verification & wrap-up. Contract/route work is
deliberately its own commit *before* any service-stack CDK code, per
constitution P-1 (boundary changes land before the implementation code that
depends on them).

## Shared services stack

- [x] Add `infra/stacks/shared_services_stack.py`: `SharedServicesStack`
  creating `ecs.Cluster` in `NetworkStack`'s VPC (`vpc_subnets` not needed
  at cluster level — subnet placement happens per-service), named
  `f"{env_name}-kiwi-cluster"`
- [x] Export `CfnOutput`s for `ClusterName`/`ClusterArn`
- [x] Register `SharedServicesStack` in `stacks/__init__.py`
- [x] Instantiate `SharedServicesStack` in `app.py`, after `NetworkStack`,
  before any service stack
- [x] Verify: `cd infra && uv run cdk synth` succeeds with `SharedServicesStack`
  alone added (service stacks don't exist yet this commit)
- [x] **Mid-implementation addition** (originally its own bullet under
  "Identity service stack" below, moved here): also creates the shared ALB
  listener (`alb.add_listener(...)`, port 80, default
  `fixed_response(404, ...)`), exported as `CfnOutput` `ListenerArn`.
  Originally planned inside `IdentityServiceStack` (built first), but that
  design had `AppApiServiceStack` reference identity's listener via a
  constructor parameter — a real bug, not just a smell: CDK cross-stack
  references become CloudFormation exports/imports, and CloudFormation
  refuses to delete a stack whose export is still imported elsewhere, so
  `cdk destroy IdentityServiceStack` would fail outright as long as
  `app-api` imports its listener. Caught during app-api implementation;
  fixed by moving the listener into this already-existing "owned by no
  service" stack, same rationale as the cluster itself. Renamed
  `ClusterStack` → `SharedServicesStack` to keep the name honest about the
  broadened scope.

## Contract + route-prefix change

- [x] Prefix `/healthz` in `contracts/identity.openapi.yaml` with
  `/identity` (`/healthz` → `/identity/healthz`)
- [x] Remove `contracts/identity.openapi.yaml`'s `/auth/token` stub
  entirely — no backing code anywhere in the repo (confirmed via grep), and
  Phase 1's Cognito-backed auth will very likely replace its guessed shape
  outright, so carrying a placeholder forward under a prefix risks it being
  mistaken for settled design
- [x] Populate `contracts/app-api/openapi.yml` (was a 0-byte empty
  file) with a minimal root OpenAPI 3.1 document declaring
  `/app-api/healthz`, matching `identity.openapi.yaml`'s shape — fixes the
  pre-existing P-1 drift where `app-api`'s working `/healthz` route had no
  contract backing at all. Left 200-only (no `default`/error-response
  entry) since the handler has no failure branch to document, and a
  shared cross-service error-response schema is deferred to Phase 2 along
  with the rest of `app-api`'s contract.
- [x] Add `backend/services/identity/identity_app/routes/health.py`: a
  `health_bp = Blueprint("health", __name__, url_prefix="/identity")` with
  the `/healthz` route, logging a line via `current_app.logger.info(...)`
  on each hit (needed to make CloudWatch verification later meaningful,
  since gunicorn's entrypoint has no `--access-logfile` flag and won't
  print per-request access logs on its own)
- [x] Add `backend/services/app-api/api_app/routes/health.py`: same
  pattern, `Blueprint("health", __name__, url_prefix="/app-api")`
- [x] Update `backend/services/identity/identity_app/__init__.py` and
  `backend/services/app-api/api_app/__init__.py` to import and
  `register_blueprint()` the new health blueprint instead of the inline
  `@app.get("/healthz")` — completing the structure each `__init__.py`'s
  own `TODO` and the already-scaffolded (empty) `app/routes/__init__.py`
  anticipated
- [x] Add a contract test to `backend/services/identity/tests/contract/`
  and `backend/services/app-api/tests/contract/` (both currently empty
  `__init__.py` placeholders — this is the first test in each, not an
  update to an existing one) asserting `GET /identity/healthz` /
  `GET /app-api/healthz` returns 200 with the `{"status": "ok"}` shape each
  contract declares — required by constitution Q-1 for the one endpoint
  this feature's contract change actually touches, not deferred to a later
  phase
- [x] Rename each service's top-level Python package from the generic
  `app` to a unique name (`identity_app`, `api_app`, `worker_app`) —
  discovered while adding the contract tests above: `uv sync
  --all-packages` installs all three services into one shared
  `backend/.venv`, and since all three previously used the same import
  name `app`, only one was ever reachable via `import app` at a time
  (silently shadowing the others). This never surfaced before because no
  test previously did a bare `from app import ...`, and production
  containers each install only one service. Updated: each service's
  `pyproject.toml` (`packages = [...]`), each `Dockerfile`'s gunicorn/
  `python -m` entrypoint, internal imports, `migrations/env.py` comments,
  `backend/pyproject.toml`'s ruff/mypy `src` list, `Makefile`'s and
  `.github/workflows/backend-ci.yml`'s `--cov=` paths, and the affected
  services' `CLAUDE.md` files.
- [x] Added `[tool.pytest.ini_options] addopts = "--import-mode=importlib"`
  to `backend/pyproject.toml` — needed once both services had a
  `tests/contract/test_healthz.py`, since neither service's `tests/` dir
  has an `__init__.py`, so both `contract` test packages collided under
  the same bare module name in pytest's default import mode.
- [x] Verify locally: `make test-backend` passes (16 passed); `curl
  localhost:<port>/identity/healthz` and `curl
  localhost:<port>/app-api/healthz` both return `{"status": "ok"}` with a
  200 against each service run standalone via its Flask dev server
  (pre-ALB, direct-to-container sanity check). **Known limitation**:
  when both services' contract tests run in the same `pytest` session,
  `pytest-cov` misreports the second-run service's `identity_app`/
  `api_app` files as 0% covered, even though the test passes and the
  route demonstrably executes (confirmed by running `coverage.py`
  directly against both apps together, which reports 100% correctly for
  both) — a `pytest-cov` measurement quirk, not an application bug.
  Doesn't affect the `--cov-fail-under=80` gate today (aggregate coverage
  is 89.92%); left undiagnosed further per explicit scope decision to move
  on rather than chase it now.

## Identity service stack

- [x] Add `infra/stacks/_fargate_service.py`: `KiwiFargateWebService(Construct)`
  — a proper CDK construct (not a bare helper function), the idiomatic CDK
  reuse pattern for something instantiated three times across three
  stacks. Named `KiwiFargateWebService` (not `FargateWebService`) to avoid
  reading as a near-duplicate of `ecs.FargateService`, which it wraps and
  exposes as `self.service` — consistent with this repo's existing
  `{env_name}-kiwi-...` resource-naming convention. Constructor:
  `KiwiFargateWebService(scope, id, *, cluster, vpc, security_group,
  image_asset_dir, dockerfile, container_port, health_check_path,
  env_name)` — dropped `alb`/`path_prefix` from the originally-planned
  signature since neither is used inside the construct (listener/rule
  wiring is stack-level, not construct-level); keeping unused params would
  just be dead code. Builds resources against `self`, exposing
  `self.service`/`self.target_group` as attributes. Internally creates a
  `FargateTaskDefinition` + container (CDK asset image from `backend/`,
  `services/<name>/Dockerfile`) + `awslogs` log group + `FargateService`
  with `circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True)` (cheap
  fast-fail on bad deployments; CDK warns without it). Left
  `minHealthyPercent` at its default (50%, meaning a momentary zero-task
  window during deploys with `desired_count=1`) since fixing it properly
  needs a second task, which `spec.md`'s "Out of scope" already defers to
  Phase 12.
- [x] Add `infra/stacks/identity_service_stack.py`: `IdentityServiceStack`
  using `KiwiFargateWebService` for `identity`; takes `SharedServicesStack`'s
  listener as a constructor input (does **not** create its own — see the
  "Shared services stack" section above for why) and adds an
  `ApplicationListenerRule` (priority `10`) matching
  `path_pattern=["/identity/*"]` forwarding to the construct's
  `target_group`, health check path `/identity/healthz`
- [x] Listener's default action (`elbv2.ListenerAction.fixed_response(404,
  ...)`, explicit "no prefix matched" response) lives in
  `SharedServicesStack` — see above — not this stack.
- [x] Register `IdentityServiceStack` in `stacks/__init__.py`; instantiate
  in `app.py`, taking `NetworkStack`'s VPC/`fargate-services-sg` and
  `SharedServicesStack`'s cluster/listener as inputs
- [x] Verify: `cd infra && uv run cdk synth` succeeds with all five stacks
  (`dev-kiwi-vpc-stack`, `dev-kiwi-shared-services-stack`, `dev-kiwi-db-stack`,
  `dev-kiwi-identity-service-stack`, `dev-kiwi-app-api-service-stack`).
- [ ] Verify: `cdk deploy SharedServicesStack IdentityServiceStack -c
  env=dev`; target group reports healthy; `curl
  http://<alb-dns>/identity/healthz` returns `{"status": "ok"}` with a 200
  through the ALB. **Not yet run** — needs real AWS credentials and a
  running Docker daemon (for the CDK asset image build), neither available
  in this environment; needs to be run manually before this task group is
  fully complete.

## App-api service stack

- [x] Add `infra/stacks/app_api_service_stack.py`: `AppApiServiceStack`
  reusing `KiwiFargateWebService` for `app-api`; takes `SharedServicesStack`'s
  listener as a constructor input (same pattern as identity, for the same
  destroy-independence reason) and adds an `ApplicationListenerRule`
  (priority `20` — distinct from identity's `10`, since AWS requires unique
  priorities per listener) matching `path_pattern=["/app-api/*"]`, health
  check path `/app-api/healthz`
- [x] Register in `stacks/__init__.py`; instantiate in `app.py`, taking the
  same shared inputs as `IdentityServiceStack`
  (`SharedServicesStack`'s cluster/listener, `NetworkStack`'s VPC/
  `fargate-services-sg`)
- [x] Verify: `cd infra && uv run cdk synth` succeeds; synthesized templates
  for both `dev-kiwi-identity-service-stack` and
  `dev-kiwi-app-api-service-stack` each contain their own
  `AWS::ElasticLoadBalancingV2::ListenerRule` referencing the one shared
  listener via cross-stack import.
- [ ] Verify: `cdk deploy AppApiServiceStack -c env=dev`; target group
  reports healthy; `curl http://<alb-dns>/app-api/healthz` returns
  `{"status": "ok"}` with a 200 through the ALB, and `/identity/healthz`
  still resolves correctly (confirms the two listener rules don't collide).
  **Not yet run** — same reason as identity's live-deploy verification
  above.

## Worker keep-alive + service stack

- [x] `backend/services/worker/worker_app/worker.py` (path corrected — the
  package rename in the earlier "Contract + route-prefix change" commit
  moved this from `app/worker.py`): add a minimal blocking loop after the
  existing `TODO` (`while True: time.sleep(3600)`) with a comment marking
  it as a Phase-0 placeholder Phase 6's real SQS polling loop replaces
  outright
- [x] Add `infra/stacks/worker_service_stack.py`: `WorkerServiceStack`.
  Rather than adding flags to `KiwiFargateWebService` to conditionally
  disable ALB attachment, added a second, separate construct —
  `KiwiFargateWorkerService` in the same `_fargate_service.py` — since
  `worker`'s shape genuinely differs (no container port, no target group,
  a `command`-based health check instead of an HTTP one) rather than being
  the same shape with one flag flipped. Duplicates ~15 lines of log
  group/task-definition/`FargateService` setup rather than sharing it,
  deliberately, per this repo's bias against premature abstraction for two
  structurally-different callers.
- [x] Container-level health check on `worker`'s task definition:
  `ecs.HealthCheck(command=["CMD-SHELL", "pgrep -f 'python -m
  worker_app.worker' || exit 1"])`
- [x] Registered `WorkerServiceStack` in `stacks/__init__.py`; instantiated
  in `app.py`, taking `NetworkStack`'s `fargate-services-sg` and
  `SharedServicesStack`'s cluster (no `vpc` or `listener` input — neither
  is used inside `KiwiFargateWorkerService`, since there's no target group
  needing `vpc` and no ALB attachment needing a `listener`; caught this
  myself before it repeated the earlier unused-parameter issue)
- [x] Verify: `cd infra && uv run cdk synth` succeeds with all six stacks.
  Inspected `dev-kiwi-worker-service-stack.template.json` directly: zero
  `AWS::ElasticLoadBalancingV2::TargetGroup`/`Listener` resources present;
  only `AWS::ECS::Service`, `AWS::ECS::TaskDefinition`, IAM, and
  `AWS::Logs::LogGroup`. `make test-backend` still passes (16 passed)
  after the `worker.py` change.
- [ ] Verify: `cdk deploy WorkerServiceStack -c env=dev`; `aws ecs
  describe-services` shows `desiredCount == runningCount == 1` with no
  `STOPPED` tasks accumulating. **Not yet run** — same reason as
  identity/app-api's open live-deploy items above.

## Docs

- [ ] Rewrite `infra/CLAUDE.md`: move `shared_services_stack.py`/
  `identity_service_stack.py`/`app_api_service_stack.py`/
  `worker_service_stack.py` out of "Not yet present" into the stack-by-stack
  description; document `SharedServicesStack`'s role (cluster + shared ALB
  listener) and why it's a separate stack (service-stack independence —
  including the destroy-coupling bug the listener hit when it was first
  tried inside `IdentityServiceStack`); document the `KiwiFargateWebService`
  construct and the `/identity`/`/app-api` path-prefix ALB routing
  convention with the plain `curl` invocation for reaching each service

## Verification & wrap-up

- [ ] Confirm all three services' tasks run in `PRIVATE_WITH_EGRESS`
  subnets, are members of `fargate-services-sg`, and have no public IP
  (`aws ecs describe-tasks` / VPC console)
- [ ] Confirm CloudWatch Logs contains each service's own log group with a
  recent entry from the health blueprint's log line (not just startup
  messages), proving the execution role's logging permission actually works
  end-to-end for real request traffic
- [ ] Confirm no task's execution or task role grants Secrets Manager or RDS
  permissions beyond pulling its own image and writing its own logs (`aws
  iam get-role-policy` / CDK-synthesized IAM policy review)
- [ ] Destroy-independence test: `cdk destroy IdentityServiceStack -c
  env=dev` alone, then confirm `app-api` and `worker`'s services are
  unaffected and still healthy/running — concrete proof `SharedServicesStack`
  (cluster *and* listener) actually decoupled the three service stacks from
  each other; redeploy `IdentityServiceStack` afterward to restore full
  state
- [ ] `cdk deploy --all -c env=dev` from a clean slate succeeds end-to-end;
  `cdk destroy --all -c env=dev` tears down all four new stacks cleanly with
  no orphaned ECS services, task definitions, clusters, or target groups
  (only exercised here as a final full-cycle check, then redeployed to leave
  the dev account in the expected running state)
- [ ] Update this feature's `spec.md`/`plan.md` if anything changed during
  implementation (constitution W-1)
- [ ] Check off the `feat-05-infra-service-shells` line in
  `specs/phases/roadmap.md`'s Phase 0 feature breakdown
