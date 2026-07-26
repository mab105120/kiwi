# Plan: Infra Service Shells

## Approach

Build bottom-up: the one truly shared resource (the ECS cluster) first,
then the contract/route-registration boundary change both HTTP services
need (constitution P-1: contract before implementation), then the two
ALB-fronted services, then the ALB-less `worker` service, then verify the
whole thing end-to-end. Each step is independently `cdk synth`-able so a
mistake is caught at the layer it's introduced, not three stacks deep.

**0. Concepts this plan assumes** (see chat for the fuller explanations
already given — this is just the vocabulary used below):
`ECS Cluster` (scheduling namespace), `Task Definition` (container blueprint:
image, CPU/memory, port, role), `Task` (one running instance of a task
definition), `Service` (keeps N tasks running, optionally attached to an ALB
target group), `Target Group` (pool of task IPs + a health check), `Listener
Rule` (decides which target group a request goes to, by path pattern here).

**1. `cluster_stack.py` — shared ECS cluster, its own stack**

- `ClusterStack` creates `ecs.Cluster(self, "Cluster", vpc=vpc,
  cluster_name=f"{env_name}-kiwi-cluster")` and exports `CfnOutput`s for
  `cluster_name`/`cluster_arn`. Takes `NetworkStack`'s VPC as its only
  constructor input.
- `IdentityServiceStack`, `AppApiServiceStack`, and `WorkerServiceStack` each
  take the cluster (via `ecs.Cluster.from_cluster_attributes(...)`, built
  from `ClusterStack`'s outputs, or the live object reference if `app.py`
  wires them directly) as a constructor input alongside `NetworkStack`'s
  VPC/security group.
- **Why a dedicated stack instead of one service stack owning it:** a
  cluster is cheap to reason about (a namespace, not a security boundary),
  so it doesn't need much ceremony — but having any one service stack own a
  resource the other two depend on means destroying that one stack breaks
  the other two. A separate `ClusterStack` means all three service stacks
  are true siblings: each depends only on `ClusterStack` + `NetworkStack`,
  never on each other, and no service's lifecycle is coupled to another
  service's. This mirrors `NetworkStack` → `DataStack`'s existing shape —
  a foundational stack multiple things build on, not one peer owning a
  resource for another peer.

**2. Contract + route-registration change for `identity` and `app-api`**

`identity` and `app-api` share one ALB (`feat-03`). Splitting traffic
between them needs *something* in the request to route on — either the URL
path or the `Host` header, since a plain ALB listener rule doesn't rewrite
paths (whatever path a rule matches, the same unmodified path is what
reaches the target group). Both contracts currently define every path
(including `/healthz`) at each service's own root, with no prefix
distinguishing one service's paths from the other's.

Resolved: **prefix every path in each contract by service name** —
`/identity/*`, `/app-api/*` — and route the ALB by path pattern against
those prefixes. This is simpler to test (`curl http://<alb-dns>/identity/
healthz`, no special headers) and, since both contracts are still
pre-Phase-1 stubs with no real endpoints or frontend clients depending on
their current shape, this is the cheapest point in the project to make this
change — doing it after Phase 1+ builds real paths and a frontend against
them would be far more disruptive.

This is a genuine boundary change (constitution P-1: contract + tests
updated *before* implementation code), so it happens first, as its own
step, before any CDK code touches these two services:

- `contracts/identity.openapi.yaml`: prefix `/healthz` with `/identity`
  (`/healthz` → `/identity/healthz`). Also **remove the `/auth/token`
  stub entirely** rather than carry it forward under a prefix — it has no
  backing code anywhere in the repo (confirmed by grep), and Phase 1's
  Cognito-backed auth (per `specs/phases/roadmap.md`) will very likely
  replace its guessed `username`/`password` shape outright, so prefixing a
  placeholder that's probably getting rewritten wholesale just risks someone
  later mistaking it for settled design.
- `contracts/app-api/openapi.yml`: this file is currently **completely
  empty** (0 bytes) despite `app-api/app/__init__.py` already serving a
  working `/healthz` route — a pre-existing P-1 violation, confirmed while
  planning this feature, not introduced by it. Fix it in this same pass:
  populate a minimal root OpenAPI document declaring `/app-api/healthz`,
  matching `identity.openapi.yaml`'s existing shape. (Wiring in
  `contracts/app-api/paths/exams.yml`'s content via `$ref` is Phase 2
  authoring work, out of scope here — this only closes the drift for the
  one endpoint that already exists in code.)
- **Dedicated blueprint module per service**, not routes inlined in
  `__init__.py`: add `backend/services/identity/app/routes/health.py`
  (`health_bp = Blueprint("health", __name__, url_prefix="/identity")`,
  `/healthz` route logging a line via `current_app.logger.info(...)` on
  each hit) and the equivalent
  `backend/services/app-api/app/routes/health.py`
  (`url_prefix="/app-api"`). This isn't a new pattern invented for this
  feature — `identity/app/__init__.py`'s own existing `TODO` already says
  "register blueprints from `app.routes` here," and both services already
  have an (empty) `app/routes/__init__.py` scaffolded for exactly this. The
  logger call inside the handler matters operationally, not just
  stylistically: the Dockerfile's `gunicorn` entrypoint has no
  `--access-logfile` flag, so gunicorn does **not** print a per-request
  access log line by default — only startup/lifecycle messages go to
  stderr regardless of traffic. Without an explicit log call, "confirm
  CloudWatch Logs shows recent entries" (Verification, step 6) could pass
  on stale startup-log evidence alone, without ever proving a live request
  was actually observed.
- `backend/services/identity/app/__init__.py` /
  `backend/services/app-api/app/__init__.py`: import and register the new
  health blueprint via `app.register_blueprint(health_bp)`.
- **Add a contract test per service** (currently, both `tests/contract/`
  directories are empty `__init__.py` placeholders with nothing to update —
  not "update existing tests," but add the first one): assert
  `GET /identity/healthz` / `GET /app-api/healthz` returns 200 with the
  `{"status": "ok"}` shape each contract declares. This is required, not
  optional, for this feature specifically: constitution Q-1 says a boundary
  change isn't "done" until its contract tests are updated, and `/healthz`
  is the one real endpoint this feature's contract change actually touches
  — deferring it to a later phase would ship this feature's boundary change
  with zero test coverage proving implementation matches contract, which is
  exactly the gap Q-1 exists to close.

**3. `identity_service_stack.py` and `app_api_service_stack.py`**

- `stacks/_fargate_service.py`: a proper CDK `Construct` subclass
  (`FargateWebService(Construct)`), not a bare helper function — this is
  the idiomatic CDK reuse pattern (it's how the CDK's own standard-library
  constructs, like `ApplicationLoadBalancedFargateService`, are built), and
  it's barely more code than a function: `super().__init__(scope, id)`,
  then build resources against `self` instead of a passed-in `scope`,
  exposing results as `self.service`/`self.target_group` attributes instead
  of a return value. Worth the small extra ceremony here since this exact
  shape is instantiated three times across three different stacks — each
  instance gets its own clean logical-ID namespace under its construct id
  automatically, which a bare function would require managing by hand.
  Constructor signature: `FargateWebService(scope, id, *, cluster, vpc,
  security_group, alb, image_asset_dir, dockerfile, container_port,
  health_check_path, path_prefix, env_name)`; internally creates:
  - `ecs.FargateTaskDefinition` (256 CPU / 512 MiB memory — the smallest
    valid Fargate combination, plenty for a `gunicorn` process serving one
    route).
  - One container via `ecs.ContainerImage.from_asset(directory="../../
    backend", file=f"services/{service_dir}/Dockerfile")` — CDK builds the
    image locally (Docker must be running wherever `cdk deploy` executes)
    and uploads it to CDK's own bootstrap ECR asset repo. This is *not* a
    hand-provisioned registry — it's the mechanism `infra/CLAUDE.md`
    already documented as the intended approach, and it's what lets this
    feature skip building a real CI image pipeline (`feat-07`'s job).
  - `logging=ecs.LogDriver.aws_logs(stream_prefix=service_name,
    log_group=logs.LogGroup(self, "LogGroup", log_group_name=f"/ecs/
    {env_name}/{service_name}", retention=logs.RetentionDays.ONE_WEEK,
    removal_policy=RemovalPolicy.DESTROY))` — one log group per service.
  - No custom execution role or task role: `FargateTaskDefinition`'s
    auto-generated execution role already grants exactly "pull this task's
    image" + "write to this task's log group" when a container + log
    driver are attached this way — already the least-privilege scope the
    spec asks for, so there's nothing to add on top.
  - `ecs.FargateService(cluster=cluster, task_definition=task_def,
    desired_count=1, security_groups=[fargate_services_sg],
    vpc_subnets=ec2.SubnetSelection(subnet_type=PRIVATE_WITH_EGRESS),
    assign_public_ip=False)`.
  - An ALB target group (`elbv2.ApplicationTargetGroup`, `target_type=IP`
    since Fargate tasks are registered by IP, not instance id) with
    `health_check=elbv2.HealthCheck(path=health_check_path, ...)` (e.g.
    `/identity/healthz`), attached via
    `service.attach_to_application_target_group(...)`. Plan uses the
    lower-level `FargateService` + manual target-group wiring rather than
    the higher-level `ApplicationLoadBalancedFargateService` construct,
    since two services need to share one ALB with routing rules between
    them, which that higher-level construct doesn't cleanly support.
- **ALB listener + rules**: one shared `elbv2.ApplicationListener` on port
  80 (created by whichever of these two stacks is deployed first, or in
  `ClusterStack` if that turns out cleaner — a small implementation detail
  to settle while coding, not a design question). Two
  `elbv2.ApplicationListenerRule`s, matching `path_pattern=["/identity/*"]`
  and `path_pattern=["/app-api/*"]`, forwarding to each service's target
  group. Default action (no path matches): `elbv2.ListenerAction.
  fixed_response(404, content_type="text/plain", message_body="not
  found")` — explicit and correct now that the two prefixes are mutually
  exclusive, rather than silently defaulting into one service's target
  group.

**4. `worker_service_stack.py`**

- Same `_fargate_service.py` construct, but via a second class (or a
  constructor parameter toggling ALB attachment off — an implementation
  choice for coding time) since `worker` gets **no** target group, load
  balancer listener rule, or public/ALB-reachable network path at all —
  only `ecs.FargateService` + `ecs.FargateTaskDefinition`.
- Task definition's container health check
  (`ecs.ContainerDefinition(..., health_check=ecs.HealthCheck(command=
  ["CMD-SHELL", "pgrep -f 'python -m app.worker' || exit 1"], interval=...,
  timeout=..., retries=...))`) — an ECS-native, command-based check, since
  there's no HTTP port to probe. This is what "healthy" means for `worker`:
  ECS runs that command *inside* the running container on an interval and
  marks the task unhealthy (and eventually replaces it) if the command
  fails, instead of the ALB's "did `/healthz` return 200" check used for
  the other two.
- **Keep-alive fix in `backend/services/worker/app/worker.py`**: `main()`
  currently returns right after its one log line, which would make the task
  exit and get replaced in a continuous restart loop rather than reach a
  stable state for the health check above to ever report on. Add the
  smallest possible blocking loop after the existing `TODO` comment (e.g.
  `while True: time.sleep(3600)`), with a comment marking it as a Phase-0
  placeholder that Phase 6's real SQS polling loop replaces outright (it
  isn't layered under the polling loop — it's what the polling loop
  *becomes*).

**5. `infra/CLAUDE.md`**

- Move `identity_service_stack.py`/`app_api_service_stack.py`/
  `worker_service_stack.py`/`cluster_stack.py` out of the "Not yet present"
  list into the stack-by-stack description; document `ClusterStack`'s role
  and the `/identity`/`/app-api` path-prefix ALB routing convention, with
  the plain `curl http://<alb-dns>/identity/healthz` invocation as how to
  reach each service (no special headers needed).

**6. Verify end-to-end**

- `cd infra && uv run cdk synth` — confirms all four new stacks synthesize,
  with the three service stacks correctly resolving `ClusterStack`'s
  exported cluster reference.
- `uv run cdk deploy ClusterStack IdentityServiceStack -c env=dev` first
  (proves the "one service stack deploys independently" acceptance
  criterion architecturally); confirm its target group reports healthy via
  `curl http://<alb-dns>/identity/healthz`.
- `uv run cdk deploy AppApiServiceStack WorkerServiceStack -c env=dev`;
  confirm app-api's health check the same way
  (`curl http://<alb-dns>/app-api/healthz`), and confirm `worker`'s ECS
  service reaches steady state (`desired_count == running_count == 1`,
  no `STOPPED` tasks accumulating) via `aws ecs describe-services`.
- Check CloudWatch Logs for all three services' log groups to confirm the
  execution role's logging permission actually works, not just that CDK
  granted it.
- As a deliberate test of the cluster/service decoupling (comment-driven
  design goal, not just an afterthought): `cdk destroy
  IdentityServiceStack -c env=dev` alone, then confirm `app-api` and
  `worker`'s services are unaffected and still healthy — this is the
  concrete proof that splitting the cluster into its own stack solved the
  coupling problem it was meant to solve.
- `cdk destroy --all -c env=dev` isn't part of routine verification here
  either (real dev account) — reserved for cleaning up a failed deploy
  while debugging.

## Risks

- **`worker`'s keep-alive loop is a real (if tiny) change to backend code**,
  not just infra — outside this feature's spec as originally scoped. It's
  the minimum needed to make the Fargate deployment demonstrable at all;
  flagged explicitly (and confirmed with the user) rather than silently
  expanded scope.
- **The contract path-prefix change is also a real scope addition**
  (`contracts/`, both services' route registration, both services'
  contract tests) beyond pure infra — flagged and confirmed with the user.
  It's a one-time boundary change made while both contracts are still cheap
  to change; any code outside this repo that already assumed the old
  unprefixed paths (there shouldn't be any yet — no frontend client exists)
  would break.
- **CDK asset-based Docker builds require Docker running wherever `cdk
  deploy` executes** (a local machine or, later, a CI runner). No issue
  today (deploys are run locally per `feat-03`'s pattern) but is the reason
  `feat-07` exists as its own feature rather than this one also trying to
  solve CI-based image builds.
- **First-time Fargate/ALB deploy for this account** — expect the first
  `cdk deploy` to surface at least one iteration (health check timing,
  security group reachability, listener-rule precedence) before targets go
  healthy; budget time for that rather than expecting a clean first pass.

## Sequencing

1. `ClusterStack`: shared ECS cluster, independent of any service stack.
2. Contract + route-registration change: prefix `/healthz` in
   `contracts/identity.openapi.yaml` and `contracts/app-api/openapi.yml`
   (fixing the latter's empty-file drift), remove `identity.openapi.yaml`'s
   unimplemented `/auth/token` stub, add each service's dedicated health
   blueprint module + contract test — lands before any CDK service stack,
   per constitution P-1.
3. `IdentityServiceStack`: `_fargate_service.py`'s `FargateWebService`
   construct introduced here (identity built first); ALB listener +
   `/identity/*` rule.
4. `AppApiServiceStack`: reuses the construct and `ClusterStack`'s cluster
   reference; adds the `/app-api/*` listener rule alongside identity's.
5. `worker/app/worker.py` keep-alive fix, then `WorkerServiceStack`
   (no ALB attachment, command-based container health check).
6. `infra/CLAUDE.md` rewrite covering the cluster stack, all three service
   stacks, and the path-prefix routing convention.
7. Deploy `ClusterStack` + identity alone, verify; deploy app-api + worker,
   verify all acceptance criteria including CloudWatch Logs, worker's
   steady-state task count, and the destroy-identity-alone decoupling test.
