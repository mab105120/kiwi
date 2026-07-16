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
manages the Python side (the CDK app), not the CLI binary or AWS auth.

## Common Commands

```
uv run cdk synth                         # render CloudFormation templates
uv run cdk diff --all -c env=dev         # show delta vs. the deployed stacks
uv run cdk deploy --all -c env=dev       # deploy NetworkStack, then DataStack
uv run cdk destroy --all -c env=dev      # tear down (RDS uses RemovalPolicy.DESTROY)
```

`env` defaults to `dev` if `-c env=...` is omitted (see `app.py`). All context
values (`account`, `region`, `db_name`, `github_repo`) live in `cdk.json`, keyed
by environment — no secrets or account IDs are hardcoded in stack code.

## Layout

- `app.py` — CDK app entrypoint. Instantiates `NetworkStack` then `DataStack`
  (in that dependency order — `DataStack` takes the VPC and security groups
  from `NetworkStack` as constructor inputs). `CiCdStack` is defined but
  commented out, not yet instantiated (wiring it up is `feat-07-deploy-pipeline`).
- `stacks/network_stack.py` — VPC (2 AZ, 1 NAT gateway, public +
  `PRIVATE_WITH_EGRESS` subnets), `db-sg` (inbound 3306 from `lambda-sg` and
  `fargate-services-sg`), `lambda-sg` (attached to the `create_db_user`
  Lambda), a dev-only SSM bastion + role (skipped when `env_name == "prod"`),
  an internet-facing ALB with `alb-sg` (inbound 80/443 from the internet — no
  listener/target group yet, nothing to route to until `feat-05` adds real
  Fargate services), and `fargate-services-sg` (inbound only from `alb-sg`,
  not yet attached to any task).
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
- Not yet present: `stacks/identity_service_stack.py`,
  `stacks/app_api_service_stack.py`, `stacks/worker_service_stack.py`
  (Fargate services behind the ALB, consuming `NetworkStack`'s
  `fargate-services-sg`/ALB outputs — `feat-05`), `stacks/frontend_stack.py`
  (S3 + CloudFront for the SPA — `feat-06`).

## Conventions

- AWS CDK v2, Python, managed with `uv` (not pip/venv).
- One shared RDS instance (see `data_stack.py`); each service's schema
  isolation is enforced at the application layer (constitution P-2), not by
  separate instances.
- Service stacks (once added by `feat-05`) build their container images from
  `backend/` as the Docker build context, per each service's Dockerfile.

## Environment configuration

`cdk.json`'s `context` block currently only populates `dev`
(`account: 453542520413`, `region: us-east-2`, `db_name: kiwidbdev`,
`github_repo: mab105120/kiwi`). The bastion/prod branching in
`network_stack.py` is written to support a `prod` context entry, but `prod`
isn't populated yet — multi-environment parameterization beyond `dev` is out
of scope until a feature actually needs it.
