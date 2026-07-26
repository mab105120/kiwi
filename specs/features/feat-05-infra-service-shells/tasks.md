# Tasks: Infra Service Shells

Seven groups below, each intended as its own commit, in the order
`plan.md`'s Sequencing lays out: Cluster stack → Contract/route-prefix
change → Identity service stack → App-api service stack → Worker keep-alive
+ service stack → Docs → Verification & wrap-up. Contract/route work is
deliberately its own commit *before* any service-stack CDK code, per
constitution P-1 (boundary changes land before the implementation code that
depends on them).

## Cluster stack

- [x] Add `infra/stacks/cluster_stack.py`: `ClusterStack` creating
  `ecs.Cluster` in `NetworkStack`'s VPC (`vpc_subnets` not needed at cluster
  level — subnet placement happens per-service), named
  `f"{env_name}-kiwi-cluster"`
- [x] Export `CfnOutput`s for `ClusterName`/`ClusterArn`
- [x] Register `ClusterStack` in `stacks/__init__.py`
- [x] Instantiate `ClusterStack` in `app.py`, after `NetworkStack`, before
  any service stack
- [x] Verify: `cd infra && uv run cdk synth` succeeds with `ClusterStack`
  alone added (service stacks don't exist yet this commit)

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

- [ ] Add `infra/stacks/_fargate_service.py`: `FargateWebService(Construct)`
  — a proper CDK construct (not a bare helper function), the idiomatic CDK
  reuse pattern for something instantiated three times across three
  stacks. Constructor: `FargateWebService(scope, id, *, cluster, vpc,
  security_group, alb, image_asset_dir, dockerfile, container_port,
  health_check_path, path_prefix, env_name)`; builds resources against
  `self`, exposing `self.service`/`self.target_group` as attributes.
  Internally creates a `FargateTaskDefinition` + container (CDK asset image
  from `backend/`, `services/<name>/Dockerfile`) + `awslogs` log group +
  `FargateService`
- [ ] Add `infra/stacks/identity_service_stack.py`: `IdentityServiceStack`
  using `FargateWebService` for `identity`; creates the shared ALB listener
  on port 80 (`elbv2.ApplicationListener`) and an `ApplicationTargetGroup` +
  `ApplicationListenerRule` matching `path_pattern=["/identity/*"]`, health
  check path `/identity/healthz`
- [ ] Set the listener's default action to
  `elbv2.ListenerAction.fixed_response(404, ...)` (explicit "no prefix
  matched" response, set here since this stack creates the listener first)
- [ ] Register `IdentityServiceStack` in `stacks/__init__.py`; instantiate
  in `app.py`, taking `NetworkStack`'s VPC/ALB/`fargate-services-sg` and
  `ClusterStack`'s cluster as inputs
- [ ] Verify: `cdk synth` succeeds; `cdk deploy ClusterStack
  IdentityServiceStack -c env=dev`; target group reports healthy; `curl
  http://<alb-dns>/identity/healthz` returns `{"status": "ok"}` with a 200
  through the ALB

## App-api service stack

- [ ] Add `infra/stacks/app_api_service_stack.py`: `AppApiServiceStack`
  reusing `FargateWebService` for `app-api`; adds an
  `ApplicationListenerRule` on identity's existing listener matching
  `path_pattern=["/app-api/*"]`, health check path `/app-api/healthz`
- [ ] Register in `stacks/__init__.py`; instantiate in `app.py`, taking the
  same shared inputs as `IdentityServiceStack` plus a reference to the
  listener `IdentityServiceStack` created
- [ ] Verify: `cdk synth` succeeds; `cdk deploy AppApiServiceStack -c
  env=dev`; target group reports healthy; `curl http://<alb-dns>/app-api/
  healthz` returns `{"status": "ok"}` with a 200 through the ALB, and
  `/identity/healthz` still resolves correctly (confirms the two listener
  rules don't collide)

## Worker keep-alive + service stack

- [ ] `backend/services/worker/app/worker.py`: add a minimal blocking loop
  after the existing `TODO` (e.g. `while True: time.sleep(3600)`) with a
  comment marking it as a Phase-0 placeholder Phase 6's real SQS polling
  loop replaces outright
- [ ] Add `infra/stacks/worker_service_stack.py`: `WorkerServiceStack` using
  a variant of `FargateWebService` (or a second construct in the same file)
  with ALB attachment disabled for `worker` — no target group, listener, or
  listener rule
- [ ] Add a container-level health check to `worker`'s task definition:
  `ecs.HealthCheck(command=["CMD-SHELL", "pgrep -f 'python -m app.worker' ||
  exit 1"], ...)`
- [ ] Register in `stacks/__init__.py`; instantiate in `app.py`, taking
  `NetworkStack`'s VPC/`fargate-services-sg` and `ClusterStack`'s cluster
  (no ALB input — `worker` doesn't need one)
- [ ] Verify: `cdk synth` succeeds; `cdk deploy WorkerServiceStack -c
  env=dev`; `aws ecs describe-services` shows `desiredCount == runningCount
  == 1` with no `STOPPED` tasks accumulating; confirm zero target groups or
  listener rules reference `worker`'s service

## Docs

- [ ] Rewrite `infra/CLAUDE.md`: move `cluster_stack.py`/
  `identity_service_stack.py`/`app_api_service_stack.py`/
  `worker_service_stack.py` out of "Not yet present" into the stack-by-stack
  description; document `ClusterStack`'s role and why it's a separate stack
  (service-stack independence); document the `FargateWebService` construct
  and the `/identity`/`/app-api` path-prefix ALB routing convention with the
  plain `curl` invocation for reaching each service

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
  unaffected and still healthy/running — concrete proof `ClusterStack`
  actually decoupled the three service stacks from each other; redeploy
  `IdentityServiceStack` afterward to restore full state
- [ ] `cdk deploy --all -c env=dev` from a clean slate succeeds end-to-end;
  `cdk destroy --all -c env=dev` tears down all four new stacks cleanly with
  no orphaned ECS services, task definitions, clusters, or target groups
  (only exercised here as a final full-cycle check, then redeployed to leave
  the dev account in the expected running state)
- [ ] Update this feature's `spec.md`/`plan.md` if anything changed during
  implementation (constitution W-1)
- [ ] Check off the `feat-05-infra-service-shells` line in
  `specs/phases/roadmap.md`'s Phase 0 feature breakdown
