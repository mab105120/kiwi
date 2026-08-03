# Infra Agent Guide

Read `/constitution.md` and `../CLAUDE.md` first.

## Setup

```
cd infra
uv sync
```

`uv sync` creates `infra/.venv` from `pyproject.toml`/`uv.lock` (`aws-cdk-lib`,
`constructs`). This is a standalone `uv`-managed project, not a member of
`backend/pyproject.toml`'s workspace — it's a CDK app with its own AWS deploy
target, not an importable Python package.

You also need the CDK CLI itself (`npm install -g aws-cdk`) and AWS credentials
for account `453542520413` (`us-east-2`) available in your environment — `uv`
manages the Python side (the CDK app), not the CLI binary or AWS auth. Service
stacks also build their container images locally via Docker at `cdk deploy`
time (CDK's asset-based image build, uploading to CDK's own bootstrap ECR
repo) — Docker must be running wherever `cdk deploy` executes.

## Common Commands

```
uv run cdk synth                         # render CloudFormation templates
uv run cdk diff --all -c env=dev         # show delta vs. the deployed stacks
uv run cdk deploy --all -c env=dev       # deploy all six stacks, in dependency order
uv run cdk destroy --all -c env=dev      # tear down (RDS uses RemovalPolicy.DESTROY)
```

`env` defaults to `dev` if `-c env=...` is omitted (see `app.py`). All context
values (`account`, `region`, `db_name`, `github_repo`) live in `cdk.json`, keyed
by environment — no secrets or account IDs are hardcoded in stack code.

Each service stack (`IdentityServiceStack`, `AppApiServiceStack`,
`WorkerServiceStack`) deploys/updates/destroys independently — e.g.
`cdk deploy IdentityServiceStack -c env=dev` or `cdk destroy
IdentityServiceStack -c env=dev` — without affecting the other two, since none
of them own a resource another depends on (see `SharedServicesStack` below).

## Layout

- `app.py` — CDK app entrypoint. Instantiates, in dependency order:
  `NetworkStack` → `SharedServicesStack` → `DataStack` →
  `IdentityServiceStack` → `AppApiServiceStack` → `WorkerServiceStack`.
  `CiCdStack` is defined but commented out, not yet instantiated (wiring it
  up is `feat-07-deploy-pipeline`).
- `stacks/network_stack.py` — VPC (2 AZ, 1 NAT gateway, public +
  `PRIVATE_WITH_EGRESS` subnets), `db-sg` (inbound 3306 from `lambda-sg` and
  `fargate-services-sg`), `lambda-sg` (attached to the `create_db_user`
  Lambda), a dev-only SSM bastion + role (skipped when `env_name == "prod"`),
  an internet-facing ALB with `alb-sg` (inbound 80/443 from the internet — the
  ALB itself is created here, but its listener is not; that lives in
  `SharedServicesStack`, below), and `fargate-services-sg` (inbound only from
  `alb-sg`, attached to all three Fargate services' tasks as of `feat-05`).
- `stacks/shared_services_stack.py` — `SharedServicesStack`: the shared ECS
  cluster (`ecs.Cluster`, named `f"{env_name}-kiwi-cluster"`) **and** the
  shared ALB listener (`elbv2.ApplicationListener` on port 80, default action
  `fixed_response(404, ...)`), both in one stack owned by no individual
  service. This matters for real reasons, not just tidiness: an earlier draft
  had `IdentityServiceStack` create the listener directly, with
  `AppApiServiceStack` referencing it via a constructor parameter.
  CDK cross-stack references become CloudFormation exports/imports, and
  CloudFormation refuses to delete a stack whose export is still imported
  elsewhere — so destroying `IdentityServiceStack` alone would have failed
  outright as long as `app-api` imported its listener, coupling the two
  services' deployment lifecycles together. `SharedServicesStack` exists so
  all three service stacks are true siblings, each depending only on
  `SharedServicesStack` + `NetworkStack`, never on each other.
- `stacks/identity_service_stack.py` / `stacks/app_api_service_stack.py` —
  `IdentityServiceStack` / `AppApiServiceStack`: an ECS Fargate service each
  (via the shared `KiwiFargateWebService` construct, below), registered with
  an ALB target group. Each adds its own `elbv2.ApplicationListenerRule`
  (distinct priority per service — `10` for identity, `20` for app-api, since
  AWS requires unique priorities per listener) onto `SharedServicesStack`'s
  shared listener, matching `path_pattern=["/identity/*"]` /
  `["/app-api/*"]` and forwarding to that service's own target group. Health
  check path is `/identity/healthz` / `/app-api/healthz`.
- `stacks/worker_service_stack.py` — `WorkerServiceStack`: an ECS Fargate
  service (via the `KiwiFargateWorkerService` construct, below) with **no**
  ALB target group, listener, or listener rule — not internet- or
  ALB-reachable at all, consistent with `backend/services/worker/CLAUDE.md`'s
  "no ALB, no HTTP server" design. Health is reported via a `command`-based
  ECS container health check (`pgrep -f 'python -m worker_app.worker'`)
  instead of an HTTP probe, since there's no port to check.
- `stacks/_fargate_service.py` — two reusable CDK `Construct` subclasses
  (not bare helper functions — the idiomatic CDK reuse pattern, matching how
  CDK's own `ApplicationLoadBalancedFargateService` is built; each gets its
  own clean logical-ID namespace under its construct id automatically):
  - `KiwiFargateWebService` — for `identity`/`app-api`. Builds a
    `FargateTaskDefinition` (256 CPU / 512 MiB — the smallest valid Fargate
    size), one container (CDK asset image from `backend/`,
    `services/<name>/Dockerfile`), an `awslogs` log group, a `FargateService`
    (`circuit_breaker=DeploymentCircuitBreaker(rollback=True)` for fast
    deployment-failure detection), and an `ApplicationTargetGroup`
    (`target_type=IP`, since Fargate tasks are registered by IP, not
    instance id) attached to that service. Exposes `self.service` /
    `self.target_group`. Named `KiwiFargateWebService` — not
    `FargateWebService` — specifically to avoid reading as a near-duplicate
    of `ecs.FargateService`, which it wraps and exposes; matches this repo's
    existing `{env_name}-kiwi-...` resource-naming convention.
  - `KiwiFargateWorkerService` — for `worker`. Same task-definition/log-group/
    `FargateService` shape, but no container port, no target group, and a
    `command`-based `ecs.HealthCheck` instead. Kept as a separate construct
    rather than adding conditional flags to `KiwiFargateWebService`, since
    `worker`'s shape is structurally different (no HTTP port or ALB
    attachment at all), not the same shape with one flag flipped.
  - Both leave `minHealthyPercent` at its 50% default (CDK warns about this)
    — with `desired_count=1`, that means a momentary zero-task window during
    deploys. Fixing it properly needs a second task, which is deliberately
    out of scope for this feature (see `spec.md`'s "Out of scope" —
    autoscaling/multi-task redundancy is a Phase 12 concern).
- `stacks/data_stack.py` — Secrets Manager (master + app-user DB credentials,
  auto-generated passwords), `DbSubnetGroup`, MySQL parameter group
  (`utf8mb4`), a `t4g.micro` `rds.DatabaseInstance` (encrypted,
  `publicly_accessible=False`, `RemovalPolicy.DESTROY`), and the
  `create_db_user` custom-resource Lambda + provider that grants the app user
  `SELECT/INSERT/UPDATE/DELETE` on the database. No S3, no SQS, no
  JWT-secret placeholder — those are later features (see `spec.md`'s "Out of
  scope").
- `stacks/cicd_stack.py` — GitHub OIDC deploy role. Exists, not instantiated
  in `app.py` yet.
- `lambda/create_db_user/` — idempotent create-user-and-grant Lambda
  (`pymysql`-based), bundled via CDK `BundlingOptions`, which installs its own
  `requirements.txt` with `pip` inside the Lambda bundling Docker image. This
  is a Lambda-runtime packaging detail, independent of the `uv`-managed CDK
  app dependencies above.
- Not yet present: `stacks/frontend_stack.py` (S3 + CloudFront for the SPA —
  `feat-06`).

## Conventions

- AWS CDK v2, Python, managed with `uv` (not pip/venv).
- One shared RDS instance (see `data_stack.py`); each service's schema
  isolation is enforced at the application layer (constitution P-2), not by
  separate instances.
- Service stacks build their container images from `backend/` as the Docker
  build context, per each service's Dockerfile, via CDK's asset system (see
  "Setup" above) — not a hand-provisioned registry or a CI-built image
  pipeline (that's `feat-07-deploy-pipeline`).
- **Path-prefix ALB routing**: `identity` and `app-api` share one ALB;
  traffic is split by URL path prefix, not `Host` header — `/identity/*`
  routes to `identity`, `/app-api/*` routes to `app-api`, each service's own
  contract (`contracts/identity.openapi.yaml` /
  `contracts/app-api/openapi.yml`) declares its paths under that prefix.
  Reach either service through the shared ALB with a plain `curl` — no
  special headers needed:
  ```
  curl http://<alb-dns>/identity/healthz
  curl http://<alb-dns>/app-api/healthz
  ```
  (`AlbDnsName` is a `CfnOutput` from `NetworkStack`, per `feat-03`.)
- No resource shared by more than one service stack (cluster, ALB listener)
  is ever created inside a service stack itself — see `SharedServicesStack`
  above for why that matters, not just as a style preference.

## Environment configuration

`cdk.json`'s `context` block currently only populates `dev`
(`account: 453542520413`, `region: us-east-2`, `db_name: kiwidbdev`,
`github_repo: mab105120/kiwi`). The bastion/prod branching in
`network_stack.py` is written to support a `prod` context entry, but `prod`
isn't populated yet — multi-environment parameterization beyond `dev` is out
of scope until a feature actually needs it.
