# Spec: Infra Service Shells

## Why

Phase 0 (`specs/phases/roadmap.md`) calls for "Fargate service shells for
`identity`, `app-api`, `worker`, each exposing only `/healthz`," deployed
end-to-end via CI/CD, as the last piece of infrastructure before the phase's
exit criteria ("empty services deploy to AWS via CDK") can be met.
`feat-03-infra-network-data` already built the VPC, the shared RDS instance,
an internet-facing ALB with `alb-sg` (80/443 from the internet), and
`fargate-services-sg` (inbound only from `alb-sg`, allowed into `db-sg`) —
but deliberately left the ALB with no listener and the security group
unattached to any task, calling that out as "the seam `feat-05`'s service
stacks attach real Fargate targets/listener rules to." `feat-04-ci-pipelines`
separately gave `identity` and `app-api` a real `/healthz` route
(`backend/services/*/app/__init__.py`) and a Docker image that CI already
builds (not pushes) on every PR. This feature is what actually runs those
images on AWS: three new CDK stacks (`identity_service_stack.py`,
`app_api_service_stack.py`, `worker_service_stack.py`, all currently listed
as "not yet present" in `infra/CLAUDE.md`) that turn the VPC/ALB/security
groups into real, running Fargate services.

The roadmap's "each exposing only `/healthz`" wording needs one correction
against what's actually in this repo: `backend/services/worker/CLAUDE.md` is
explicit that `worker` is "asynchronous, SQS-driven... No ALB, no HTTP
server" — it has no Flask app, no `/healthz` route, and no OpenAPI contract
at all (its boundary contract is `contracts/messages/grading-job.schema.json`,
not an HTTP path). That split was a deliberate architecture decision made
before this feature, not an oversight this feature should reverse by bolting
an HTTP server onto `worker` just to satisfy a literal reading of the
roadmap bullet. So this feature treats "expose only `/healthz`" as applying
to the two services that actually have HTTP servers (`identity`, `app-api`)
— each gets a real ALB target group whose health check hits its existing
`/healthz` route — while `worker`'s Fargate service is health-checked the
way a process with no listening port normally is on ECS: a container-level
health check (`HEALTHCHECK`/ECS `healthCheck` command), with no ALB
attachment, no target group, and no change to `alb-sg`/`fargate-services-sg`
beyond what `feat-03` already opened.

Nothing here adds real functionality to any service — no auth, no exam
data, no grading. It's the compute layer under empty containers, matching
the phase's own framing ("a deployable skeleton with nothing functional
yet").

One more pre-existing gap surfaced while planning this feature, worth
folding in here rather than leaving as a separate cleanup:
`contracts/app-api/openapi.yml` is currently a completely empty file, even
though `app-api/app/__init__.py` already serves a working `/healthz` route
— a real violation of constitution P-1 ("code never defines a boundary the
contract doesn't describe"). Since this feature already needs to touch both
services' contracts to give `identity` and `app-api` distinct path
namespaces (so the shared ALB can route between them by path — see below),
it fixes this drift in the same pass rather than deferring it.

## Routing design

`identity` and `app-api` share one ALB (`feat-03`), and their OpenAPI
contracts previously defined all paths (including `/healthz`) at each
service's root with no distinguishing prefix. Routing between two services
sharing one load balancer needs *something* to distinguish requests by —
either the request path or the `Host` header, since a plain ALB listener
rule doesn't rewrite paths (whatever path pattern a rule matches, the
unmodified original path is what reaches the target). After review, this
feature prefixes each service's contract paths by service name —
`/identity/*` and `/app-api/*` — and routes the ALB by path pattern against
those prefixes. This is a **contract (boundary) change**, so
`contracts/identity.openapi.yaml` and `contracts/app-api/openapi.yml`, each
service's route registration, and each service's `tests/contract/` suite
are in scope for this feature (constitution P-1: contract and tests updated
before implementation). Doing it now — while both contracts are still
pre-Phase-1 stubs with no real endpoints or frontend clients depending on
their current shape — is far cheaper than doing it after Phase 1+ adds real
paths.



## Scope

- **Four new CDK stacks** under `infra/stacks/`: a shared
  `shared_services_stack.py` plus one stack per backend service —
  `identity_service_stack.py`, `app_api_service_stack.py`,
  `worker_service_stack.py` — matching the service-stack layout
  `infra/CLAUDE.md` already anticipates, plus the small shared-services
  stack the three service stacks depend on. Each service stack is
  deployed/updated/destroyed independently (its own CloudFormation stack),
  so a change to one service's task definition can't block or blast-radius
  the other two; all three depend only on `shared_services_stack.py` and
  `NetworkStack`, never on each other, so no service stack's lifecycle is
  coupled to another service's. Each takes `NetworkStack`'s VPC,
  `fargate-services-sg`, and `shared_services_stack.py`'s cluster as
  constructor inputs (plus, for `identity`/`app-api`, its shared ALB
  listener) — the same dependency-injection pattern `DataStack` already
  uses for VPC/security groups.
  - `identity_service_stack.py` and `app_api_service_stack.py`: an ECS
    Fargate service each, registered with an ALB target group whose health
    check path is `/identity/healthz` / `/app-api/healthz` respectively (see
    "Routing design" above for the prefix). Each adds its own ALB listener
    rule (distinct priority per service) onto `shared_services_stack.py`'s
    listener, routing by path pattern (`/identity/*`, `/app-api/*`) to its
    own target group — this spec requires that each service is
    independently reachable through the existing ALB by its own path
    prefix and that its target group reports healthy.
  - `worker_service_stack.py`: an ECS Fargate service with **no** ALB
    target group, listener, or listener rule — it is not internet- or
    ALB-reachable at all, consistent with `backend/services/worker/CLAUDE.md`.
    Health is reported via an ECS task-definition container health check
    (a command-based check, since there is no HTTP port to probe), not an
    ALB health check.
  - Common CDK shape shared by the three service stacks (task-definition
    scaffolding, log-group setup) is factored into a small shared CDK
    `Construct` (e.g. `stacks/_fargate_service.py`'s `KiwiFargateWebService`
    — named to avoid reading as a near-duplicate of the `ecs.FargateService`
    it wraps) rather than copy-pasted three times — an implementation detail
    for `plan.md`, not a fifth stack.
- **A shared ECS cluster and ALB listener**, both defined once in
  `shared_services_stack.py` (not owned by any one service stack, so
  destroying one service stack never affects the others' ability to run —
  this applies to the listener too: an earlier draft had `identity`'s stack
  create the shared listener directly, which would have made
  `AppApiServiceStack`'s listener-rule reference block `identity`'s stack
  from ever being destroyed independently, defeating the whole point).
  Cluster is placed in the VPC's private subnets — the same
  `PRIVATE_WITH_EGRESS` subnets `feat-03` already created — and both are
  exposed as `CfnOutput`s.
- **Contract + route-registration changes for `identity` and `app-api`**
  (see "Routing design" above): prefix `/healthz` in
  `contracts/identity.openapi.yaml` with `/identity` and in
  `contracts/app-api/openapi.yml` with `/app-api` (including adding the
  missing `/app-api/healthz` declaration — see "Why"). Also remove
  `identity.openapi.yaml`'s unimplemented `/auth/token` stub — it has no
  backing code anywhere in the repo, and Phase 1's Cognito-backed auth will
  very likely replace its guessed shape entirely, so carrying a placeholder
  forward under a new prefix adds risk (someone mistaking it for settled
  design) without preserving anything real. Update each service's Flask
  route registration as a dedicated blueprint module (e.g.
  `app/routes/health.py`, matching the `url_prefix`) imported and registered
  from `create_app()` — completing the structure
  `app/__init__.py`'s existing `TODO` and the already-scaffolded
  `app/routes/` package anticipate, rather than inlining routes in
  `__init__.py`. Add a minimal `tests/contract/` test per service asserting
  the new prefixed `/healthz` path returns the shape the contract declares
  — constitution Q-1 requires this for any endpoint whose contract changes,
  and `/healthz` is the one endpoint this feature actually touches.
- **Container images built from the existing Dockerfiles**, using `backend/`
  as the build context (`services/identity/Dockerfile`,
  `services/app-api/Dockerfile`, `services/worker/Dockerfile`) exactly as
  `infra/CLAUDE.md` already documents as the intended approach — no new
  container registry, no image-push step. This feature only needs an image
  to exist at deploy time, not to distribute one; wiring a real
  build-and-push pipeline is `feat-07-deploy-pipeline`.
- **Task execution role(s)** scoped to what an empty `/healthz`-only
  container actually needs: pull its own image, write its own CloudWatch
  Logs group. No Secrets Manager or RDS grants yet — none of the three
  services read config or open a DB connection today (each `create_app()`/
  `worker.py` has a `TODO` for that), so granting DB-secret access now would
  be provisioning ahead of code that doesn't use it.
- **Each Fargate task attached to `fargate-services-sg`** (the security
  group `feat-03` already created for exactly this purpose) — no new
  security group, no change to `alb-sg` or `db-sg` beyond what `feat-03`
  already opened.
- Minimal task sizing (smallest Fargate CPU/memory combination that runs a
  `gunicorn`/Python process) and a single task per service — this is a
  skeleton, not a capacity-planned deployment.
- **A minimal keep-alive change to `backend/services/worker/app/worker.py`**:
  today `main()` logs `"worker starting"` and returns immediately, which
  would make its Fargate task exit and get relaunched in a continuous crash
  loop rather than reach a stable running state. This feature adds just
  enough of a blocking loop to keep the process alive between deploys — not
  the real SQS polling loop, which stays a `TODO` for Phase 6 — clearly
  marked as a placeholder for that later feature to replace.
- Update `infra/CLAUDE.md` to describe the actual stack contents once these
  four stacks exist (moving the three service stacks out of the "not yet
  present" list) and to document the shared ECS cluster and the
  `/identity`/`/app-api` path-prefix routing convention.

## Out of scope

- **Fleshing out `contracts/app-api/openapi.yml` beyond the `/app-api/healthz`
  fix above** — in particular, wiring in `contracts/app-api/paths/exams.yml`'s
  existing content via `$ref`. That's Phase 2 authoring work
  (`specs/phases/roadmap.md`), not this feature; this feature only closes
  the P-1 drift for the one endpoint that already exists in code.
- **Any real endpoint** beyond `/healthz` for `identity`/`app-api`, or any
  SQS consumption logic for `worker`. Those are Phase 1 (identity) and
  Phase 6 (worker grading) respectively — this feature only needs the
  containers that already exist to run and report healthy.
- **Building and pushing images via CI/CD**, or any ECR repository. Images
  are built locally by the CDK asset system at deploy time, per
  `infra/CLAUDE.md`'s existing description. A real CI-built, registry-backed
  image pipeline is `feat-07-deploy-pipeline`.
- **`frontend_stack.py`** (S3 + CloudFront) — `feat-06-infra-frontend-shell`.
- **Instantiating `cicd_stack.py`** in `app.py` — still `feat-07`.
- **HTTPS/TLS on the ALB's client-facing listener, a custom domain, or
  Route53.** `feat-03` already deferred this; this feature doesn't need it
  either since there's still no real user-facing traffic to protect. Note
  this is specifically about the ALB *listener* (client → ALB) — the ALB →
  task hop on the target group is `HTTP` regardless and stays that way even
  after TLS is added on the listener side, since that hop never leaves the
  private VPC (standard terminate-TLS-at-the-load-balancer pattern). Getting
  a real listener certificate needs an owned domain + ACM + likely Route53,
  none of which exist in this repo yet; tracked as a named bullet under
  Phase 12 (`specs/phases/roadmap.md`) rather than assigned to any feature
  yet.
- **Autoscaling policies, CloudWatch alarms/dashboards, or multi-task
  redundancy.** One task per service is enough to prove the deploy path;
  scaling is a Phase 12 hardening concern.
- **Wiring DB or Secrets Manager access into any service's task.** Deferred
  until a service actually needs a DB connection (Phase 1 for `identity`).
- **Database migrations or schema creation** for any service — unrelated to
  standing up compute, and each service's own `alembic` concern per
  `backend/CLAUDE.md`.
- **Multi-environment (staging/prod) parameterization** beyond what
  `feat-03` already left in `cdk.json` — `dev` only.
- **Changing `alb-sg`, `fargate-services-sg`, or `db-sg`** as defined in
  `feat-03`'s `network_stack.py`. This feature consumes those security
  groups as-is; it doesn't need new rules beyond what's already open.

## Acceptance criteria

- [ ] `cd infra && cdk synth` succeeds with `app.py` instantiating
  `SharedServicesStack`, `IdentityServiceStack`, `AppApiServiceStack`, and
  `WorkerServiceStack`, in addition to the existing `NetworkStack`/
  `DataStack`, each service stack taking its VPC/security-group/listener/
  cluster inputs from `NetworkStack`'s and `SharedServicesStack`'s outputs
  (no duplicate VPC, cluster, listener, or security-group creation across
  stacks).
- [ ] `contracts/identity.openapi.yaml` and `contracts/app-api/openapi.yml`
  declare all paths under `/identity` and `/app-api` respectively (including
  `/app-api/healthz`, previously missing entirely); each service's
  `tests/contract/` suite passes against its own updated contract.
- [ ] `cdk deploy --all -c env=dev` succeeds; the `identity` and `app-api`
  ALB target groups both report their (single) target as healthy, using
  `/identity/healthz` / `/app-api/healthz` as the health check path.
- [ ] Hitting the ALB's DNS name (`AlbDnsName`, from `feat-03`) at
  `/identity/healthz` and `/app-api/healthz` — no special headers required —
  gets back `{"status": "ok"}` with a 200 from the correct service, through
  the ALB's path-based listener rules, not by hitting a task directly.
- [ ] The `worker` Fargate service runs with zero ALB target groups,
  listeners, or listener rules referencing it, and its task shows healthy
  via its container-level health check rather than any HTTP probe.
- [ ] All three services' tasks run in the VPC's private
  (`PRIVATE_WITH_EGRESS`) subnets and are members of `fargate-services-sg`;
  no task has a public IP.
- [ ] Each service's container logs are visible in CloudWatch Logs (proving
  the task execution role's logging permission works), scoped to that
  service's own log group.
- [ ] No task's execution or task role grants Secrets Manager or RDS
  permissions beyond what pulling its image and writing its own logs
  requires.
- [ ] `cdk deploy IdentityServiceStack -c env=dev` (or any one service stack
  alone) succeeds without requiring a redeploy of the other two service
  stacks — confirming they're genuinely independent stacks, not one stack
  split across files, and not coupled to each other (only to
  `SharedServicesStack`).
- [ ] Destroying any one service stack (e.g. `cdk destroy
  IdentityServiceStack -c env=dev`) does not affect the other two service
  stacks' ability to keep running — confirming the shared cluster and
  listener's independence from any single service's lifecycle.
- [ ] `cdk destroy --all -c env=dev` tears down all four new stacks cleanly
  with no orphaned ECS services, task definitions, clusters, or target
  groups.
- [ ] `infra/CLAUDE.md` reflects the actual stack contents (cluster stack +
  three service stacks) and the path-prefix routing convention, replacing
  the current "not yet present" note.
