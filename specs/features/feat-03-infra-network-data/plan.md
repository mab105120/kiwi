# Plan: Infra Network & Data Stacks

## Approach

This is a migration-plus-extension, not a greenfield build. Copy the
standalone `kiwi-cloud-config` project's source into `kiwi/infra/` first
(with renames), confirm it still synthesizes unchanged, *then* layer in the
ALB/security-group additions. Doing the pure copy first isolates "did the
migration break anything" from "did the new code break anything" — if
`cdk synth` fails after step 1, it's a path/import problem, not a logic
problem.

**1. Migrate CDK app tooling, switching pip+venv to `uv`**

- Copy into `infra/`: `app.py`, `cdk.json`, `cdk.context.json`,
  `stacks/__init__.py`, `stacks/vpc_stack.py` → `stacks/network_stack.py`,
  `stacks/database_stack.py` → `stacks/data_stack.py`, `stacks/cicd_stack.py`
  (unchanged, still not instantiated in `app.py`), `lambda/create_db_user/`
  (unchanged, including its own `requirements.txt` — that's a Lambda
  bundling detail, untouched by this step).
- Do **not** copy `requirements.txt` (the CDK app's own, at the repo root of
  `kiwi-cloud-config`) or `venv/`. Instead add `infra/pyproject.toml`:
  `[project]` with `aws-cdk-lib`/`constructs` as dependencies (same version
  floors as the source `requirements.txt`), `requires-python` matching the
  source repo's Python 3.11 (Lambda runtime + CI already pin 3.11 — no
  reason to bump it as part of this migration), a `[tool.uv]` block with
  `package = false` (an app, not an importable package — mirrors
  `backend/pyproject.toml`'s own `package = false`), and a `dev` dependency
  group for `ruff`/`mypy` if `infra/CLAUDE.md`'s conventions call for lint
  tooling here too (check that file's current conventions section; add only
  if it does, to avoid inventing new scope).
- Run `uv lock` to generate `infra/uv.lock`, then `uv sync` to create
  `infra/.venv`.
- Update class names/imports for the renamed files (`VpcStack` →
  `NetworkStack`, `DatabaseStack` → `DataStack` in `stacks/__init__.py` and
  `app.py`) — pure rename, no behavior change.
- Do not copy: `local/` (stale draft spec/notes), `.github/workflows/*.yml`
  (repo-root-path assumptions, belongs to `feat-04`/`feat-07`).
- Verify: `cd infra && uv sync && uv run cdk synth` succeeds and produces
  the same two stacks with no diff in resource shape from the source repo's
  last deployed state.
- Stack id naming: source repo used `{env}-kiwi-vpc-stack` /
  `{env}-kiwi-db-stack`. Since these already exist as deployed CloudFormation
  stacks under those names in account `453542520413`, keep the **same stack
  ids** in `app.py` (do not rename to `-network-stack`/`-data-stack`) so
  `cdk deploy` updates the existing stacks in place instead of creating
  duplicates alongside them. Only the *file names* change to match
  `infra/CLAUDE.md`'s convention — the deployed `CfnStack` identity does not.
- `db_name`/app-user naming (`kiwidbdev`/`kiwidbuser`) is carried over
  unchanged — no rename in this feature (see spec.md's "Out of scope").

**2. Extend `network_stack.py` with ALB + Fargate security group**

- Add `alb-sg`: `ec2.SecurityGroup`, `allow_all_outbound=False`, ingress
  80/443 from `ec2.Peer.any_ipv4()`.
- Add `fargate-services-sg`: `ec2.SecurityGroup`, `allow_all_outbound=True`
  (services need outbound to RDS, and later S3/external APIs), no ingress
  yet except via `add_ingress_rule(peer=alb_sg, connection=ec2.Port.all_tcp())`
  — `feat-05` narrows this to specific container ports per service when it
  adds real target groups.
- Add `db_security_group.add_ingress_rule(peer=fargate_services_sg,
  connection=ec2.Port.tcp(3306), ...)` alongside the existing `lambda-sg`
  rule.
- Add `elbv2.ApplicationLoadBalancer` in the public subnets, internet-facing,
  security group = `alb-sg`. No listener/target group yet (nothing to route
  to) — `feat-05` adds those when real Fargate services exist. CDK requires
  at least a default action if a listener is added at all, so skip adding a
  listener in this feature entirely rather than stubbing a fake one.
- Add the new `CfnOutput`s listed in spec.md
  (`AlbArn`/`AlbDnsName`/`AlbSecurityGroupId`/`FargateServicesSecurityGroupId`
  /`PublicSubnetIds`/`PrivateSubnetIds`).

**3. Rewrite `infra/CLAUDE.md`**

- Replace the source repo's pip+venv `## Setup` section with the `uv`
  equivalent (`uv sync`); replace `## Common Commands` entries with their
  `uv run` forms (`uv run cdk synth`, `uv run cdk deploy --all -c env=dev`,
  `uv run cdk diff --all -c env=dev`, `uv run cdk destroy --all -c
  env=dev`).
- Update `## Architecture` / `### Stack layout` to describe
  `NetworkStack`/`DataStack` under their new names and the ALB/SG additions;
  keep the `CiCdStack` description but note it's not yet instantiated
  (unchanged from source).
- Leave `### Environment configuration` as-is (`db_name: "kiwidbdev"`,
  unchanged).

**4. Verify end-to-end**

- `uv run cdk diff --all -c env=dev` against the real, already-deployed
  stacks (same account/stack-ids as step 1) to see the actual delta before
  deploying — should show only the new ALB/security-group resources, nothing
  else.
- `uv run cdk deploy --all -c env=dev` — confirm ALB/SGs create cleanly.
- `uv run cdk destroy --all -c env=dev` is **not** run as part of normal
  verification (this hits a real, in-use dev account) — only exercised if
  something needs to be torn down and rebuilt to debug a failed deploy.

## Risks

- **Switching pip+venv to `uv` changes how the CDK CLI's Python side is
  invoked** (`cdk synth`/`cdk deploy` need to run inside `uv`'s venv, i.e.
  `uv run cdk ...`, or with `infra/.venv` activated) but does not change
  what gets synthesized — `aws-cdk-lib`/`constructs` pinned to the same
  versions either way. Confirm `uv run cdk synth`'s output is
  byte-for-byte-equivalent (modulo asset hashes) to what the source repo
  last deployed, so the tooling swap is verified as behavior-neutral before
  the ALB/SG additions land on top of it.
- **This targets a real, already-deployed AWS account** (`453542520413`),
  not a fresh sandbox. Migrating the existing `NetworkStack`/`DataStack`
  code should be a no-op diff on `cdk deploy` (same stack ids, same logical
  resource ids from the unchanged constructs) — confirm this with `cdk diff`
  *before* deploying, since an unexpected diff on the existing VPC/RDS would
  mean something about the migration (construct id, prop ordering) isn't as
  identical as intended.
- **Stack-id continuity.** Getting the stack ids wrong (e.g. accidentally
  renaming them to match the new file names) would make CDK create brand-new
  stacks instead of updating the existing ones, leaving the old
  `dev-kiwi-vpc-stack`/`dev-kiwi-db-stack` orphaned. Double-check `app.py`
  before the first `cdk deploy` from this repo.
- **No listener on the new ALB.** An ALB with no listener is a valid but
  inert resource — confirmed intentional (nothing to route to yet), but
  worth calling out so a reviewer doesn't assume it's an oversight.
- **`fargate-services-sg` ingress is `all_tcp` from `alb-sg`**, broader than
  it'll eventually need to be once real container ports are known. Acceptable
  for Phase 0 (nothing is attached to it yet); `feat-05` should narrow it.

## Sequencing

1. Copy `kiwi-cloud-config` source into `infra/` with file renames and the
   pip+venv → `uv` tooling switch (no stack logic changes, no
   `db_name`/app-user rename); verify `uv run cdk synth` matches
   pre-migration shape.
2. Add ALB, `alb-sg`, `fargate-services-sg`, and the new `db-sg` ingress rule
   to `network_stack.py`; add new `CfnOutput`s.
3. Rewrite `infra/CLAUDE.md` for the migrated + extended layout (`uv`
   commands, updated stack layout).
4. `uv run cdk diff --all -c env=dev`, review the delta, then `uv run cdk
   deploy --all -c env=dev` against the real dev account; confirm all
   acceptance criteria.
