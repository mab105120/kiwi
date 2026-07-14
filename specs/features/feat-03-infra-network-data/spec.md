# Spec: Infra Network & Data Stacks

## Why

Phase 0 (`specs/phases/roadmap.md`) needs a real, deployable network and data
foundation on AWS before any compute (Fargate services, `feat-05`) or frontend
hosting (`feat-06`) can be stacked on top of it. Right now `infra/` contains
only a `CLAUDE.md` describing the intended stack layout (`app.py`,
`stacks/network_stack.py`, `stacks/data_stack.py`) — none of it exists in this
repo yet.

It doesn't need to be built from scratch, though: a working, previously
-deployed standalone CDK project already exists at
`../kiwi-cloud-config` (account `453542520413`, region `us-east-2`) with a
`VpcStack` (VPC, subnets, `db-sg`/`lambda-sg` security groups, dev-only SSM
bastion) and a `DatabaseStack` (encrypted RDS MySQL, Secrets Manager
credentials, a `create_db_user` custom-resource Lambda that provisions a
least-privileged app DB user). That project predates this repo's
`contracts/`, `constitution.md`, and service split, so it has no ALB and no
Fargate-facing security group — but its VPC and database plumbing is sound
and should be migrated in, not rewritten.

This feature migrates that code into `infra/` (renamed to match
`infra/CLAUDE.md`'s `network_stack.py`/`data_stack.py` layout) and extends it
with the one piece the roadmap needs that the standalone project never had:
an ALB + Fargate-facing security group (for `feat-05` to attach to later).
`stacks/cicd_stack.py` (GitHub OIDC deploy role) also migrates over but stays
uninstantiated in `app.py`, exactly as it is in the source repo today —
wiring it up is `feat-07-deploy-pipeline`.

SQS (the grading-job queue behind `contracts/messages/
grading-job.schema.json`) is deliberately **not** part of this feature — see
"Out of scope". It's a `worker`/grading-pipeline concern (Phase 6) and gets
built alongside that feature, not speculatively here.

## Scope

- **Migrate CDK app tooling** from `kiwi-cloud-config` into `infra/`:
  `app.py`, `cdk.json` (context: `account`, `region`, `db_name`,
  `github_repo`), `cdk.context.json`, and the stack/dependency contents
  (`aws-cdk-lib`, `constructs`) currently listed in that repo's
  `requirements.txt` — but switch dependency management from pip+venv to
  `uv` (an `infra/pyproject.toml` + `uv.lock`, `uv sync` to install,
  `uv run cdk synth`/`uv run cdk deploy` to invoke the CDK CLI's Python
  side) so `infra/` uses the same toolchain as `backend/` instead of
  introducing a second one. `infra/` isn't a member of
  `backend/pyproject.toml`'s uv workspace (it's a standalone CDK app with
  its own AWS deploy target, not a Python package other services import),
  so this is its own `uv`-managed project, not an addition to that
  workspace.
- **`stacks/network_stack.py`** (renamed from `vpc_stack.py`, reused as-is
  plus additions):
  - Keep: VPC (2 AZ, 1 NAT gateway, public + `PRIVATE_WITH_EGRESS` subnets),
    `db-sg` (inbound 3306 from `lambda-sg` only), `lambda-sg` (attached to the
    `create_db_user` Lambda), the dev-only SSM bastion + role (skipped when
    `env_name == "prod"`).
  - Add: an ALB in the public subnets with an `alb-sg` (inbound 80/443 from
    the internet) and a `fargate-services-sg` (inbound only from `alb-sg`,
    not yet attached to any task) — the seam `feat-05`'s service stacks
    attach real Fargate targets/listener rules to. Add `fargate-services-sg`
    as an additional inbound source on `db-sg` (3306), alongside the existing
    `lambda-sg` rule, so services can reach RDS once `feat-05` lands.
  - Keep existing `CfnOutput`s (`VpcId`, `DbSecurityGroupId`,
    `LambdaSecurityGroupId`, `BastionInstanceId`); add `AlbArn`/`AlbDnsName`,
    `AlbSecurityGroupId`, `FargateServicesSecurityGroupId`,
    `PublicSubnetIds`, `PrivateSubnetIds`.
- **`stacks/data_stack.py`** (renamed from `database_stack.py`, reused as-is
  plus one rename):
  - Keep: two Secrets Manager secrets (master + app-user credentials,
    auto-generated passwords), `DbSubnetGroup`, MySQL parameter group
    (`utf8mb4`), the `t4g.micro` `rds.DatabaseInstance` (encrypted,
    `publicly_accessible=False`, `RemovalPolicy.DESTROY`), and the
    `create_db_user` custom-resource Lambda + provider that grants the app
    user `SELECT/INSERT/UPDATE/DELETE` on the database.
  - Keep `db_name` (`kiwidbdev`) and the app-user secret's `username`
    (`kiwidbuser`) exactly as they are in the source repo. Aligning these
    with `docker-compose.yml`'s local naming (`platform`/`platform`) is a
    real improvement worth doing, but it touches a live, already-deployed
    database and deserves its own change, not a drive-by inside this
    migration — deferred, see "Out of scope".
  - No S3, no SQS, no JWT-secret placeholder in this feature — see "Out of
    scope".
- **`lambda/create_db_user/`** — copied over unchanged, including its own
  `requirements.txt` (idempotent create-user-and-grant Lambda,
  `pymysql`-based, bundled via CDK `BundlingOptions`, which installs that
  `requirements.txt` with `pip` inside the Lambda bundling Docker image).
  That's a Lambda-runtime packaging detail, unrelated to local dev tooling —
  the `uv` switch above only applies to how a developer/CI installs the CDK
  app's own dependencies, not how Lambda assets are bundled.
- **`stacks/cicd_stack.py`** — copied over unchanged, still not instantiated
  in `app.py` (matches the source repo's current state). Out of scope to
  wire up; that's `feat-07-deploy-pipeline`.
- Rewrite `infra/CLAUDE.md` to describe the actual migrated+extended layout:
  `uv`-based setup/common-commands (replacing the source repo's pip+venv
  instructions) and stack descriptions updated for the ALB/SG additions.

## Out of scope

- **Renaming `db_name`/app-user to `platform`** to match local
  docker-compose naming. Real value, but it's a change against a live
  database (not just new resources), so it gets its own feature/change once
  there's a reason to touch it rather than bundling it into an
  infra-migration change. `db_name` stays `kiwidbdev`, app-user stays
  `kiwidbuser`.
- **SQS grading-job queue + DLQ.** `contracts/messages/
  grading-job.schema.json` defines the message shape, but there's no
  producer (`app-api`) or consumer (`worker`) yet — both are Phase 6 work.
  Provisioning the queue now would be infra speculating ahead of the
  application feature that actually needs it. Build it as part of whichever
  feature first wires `worker`'s SQS consumption (Phase 6 `feat-*`), not
  here.
- **S3 buckets** for submissions/artifacts. Same reasoning as SQS — no
  feature reads/writes them yet (first real use is assignment file upload,
  Phase 9). Add them in that feature instead of provisioning empty buckets
  speculatively.
- **`JWT_SIGNING_SECRET` placeholder in Secrets Manager.** `platform_common`
  (`feat-02`) reads it from a local env var today; wiring a real Secrets
  Manager-backed secret is `identity` (Phase 1) becoming a real issuer, not
  this feature.
- Any Fargate service stack (`identity_service_stack.py`,
  `app_api_service_stack.py`, `worker_service_stack.py`) — `feat-05`, which
  depends on this feature's VPC/ALB/security-group outputs.
- `frontend_stack.py` (S3 + CloudFront for the SPA) — `feat-06`.
- Instantiating `cicd_stack.py` in `app.py`, and migrating/adapting the
  standalone repo's `.github/workflows/*.yml` (they reference repo-root
  paths, not an `infra/` subdirectory) — `feat-04-ci-pipelines` and
  `feat-07-deploy-pipeline`.
- Running database migrations or creating per-service MySQL schemas inside
  the RDS instance — the instance + app user exist and are reachable; schema
  ownership/migrations remain each service's `alembic` concern.
- Multi-environment (staging/prod) parameterization beyond what already
  exists in `cdk.json`'s context structure (`dev` today; the bastion/prod
  branching in `network_stack.py` is preserved as-is but `prod` context isn't
  populated in this change).
- Route53/custom domain/TLS certificate for the ALB — plain HTTP/ALB DNS name
  is enough for Phase 0.
- Reconciling `kiwi-cloud-config`'s stale `local/spec-doc.md` (an early draft
  that predates this repo's constitution/contracts/service split) — this
  repo's `constitution.md` and `specs/` are authoritative; that file is not
  migrated.

## Acceptance criteria

- [ ] `cd infra && cdk synth` succeeds with no errors against an `app.py`
  that instantiates `NetworkStack` and `DataStack` (in that dependency
  order), reading `env`/context from `cdk.json` as the source repo did.
- [ ] `NetworkStack` synthesizes the migrated VPC/subnets/`db-sg`/`lambda-sg`
  /bastion unchanged, plus a new ALB, `alb-sg` (80/443 from internet only),
  and `fargate-services-sg` (inbound only from `alb-sg`); `db-sg` allows
  inbound 3306 from both `lambda-sg` and `fargate-services-sg`, nothing else.
- [ ] `DataStack` synthesizes the migrated RDS instance, master + app-user
  secrets (`kiwidbuser`/`kiwidbdev`, unchanged from the source repo), and
  `create_db_user` custom resource unchanged in behavior — no SQS, S3, or
  JWT-secret resources are created by this feature.
- [ ] `DataStack` takes the VPC, `db-sg`, and `lambda-sg` from `NetworkStack`
  as constructor inputs (no duplicate VPC/SG creation), and exposes
  `CfnOutput`s for every resource identifier later features will need.
- [ ] `cdk deploy --all -c env=dev` against the existing AWS account
  (`453542520413`/`us-east-2`) succeeds end-to-end; every output resolves to
  a real resource; the app DB user can connect and is scoped to
  `SELECT/INSERT/UPDATE/DELETE` on the `kiwidbdev` database only.
- [ ] `cdk destroy --all -c env=dev` tears down cleanly with no orphaned
  resources (RDS uses `RemovalPolicy.DESTROY` deliberately, as in the source
  repo).
- [ ] No secrets, credentials, account IDs, or ARNs are hardcoded/committed
  outside `cdk.json`'s non-secret context values (constitution T-4) —
  synthesized values only.
- [ ] `infra/CLAUDE.md` documents the migrated setup/deploy workflow and
  reflects the actual stack contents (not the pre-migration description).
