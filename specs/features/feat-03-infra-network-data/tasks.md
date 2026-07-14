# Tasks: Infra Network & Data Stacks

Four groups below, each intended as its own commit, in order: Migration →
Network additions → Docs → Verification & wrap-up.

## Migration

- [ ] Copy `kiwi-cloud-config/app.py`, `cdk.json`, `cdk.context.json`,
  `stacks/__init__.py` into `infra/` (not `requirements.txt` — replaced by
  `uv` tooling below)
- [ ] Copy `stacks/vpc_stack.py` into `infra/stacks/network_stack.py`,
  renaming the class `VpcStack` → `NetworkStack`
- [ ] Copy `stacks/database_stack.py` into `infra/stacks/data_stack.py`,
  renaming the class `DatabaseStack` → `DataStack`
- [ ] Copy `stacks/cicd_stack.py` into `infra/stacks/cicd_stack.py`
  unchanged (still not instantiated in `app.py`)
- [ ] Copy `lambda/create_db_user/` into `infra/lambda/create_db_user/`
  unchanged, including its own `requirements.txt` (Lambda bundling detail,
  unrelated to the CDK app's own tooling)
- [ ] Add `infra/pyproject.toml`: `aws-cdk-lib`/`constructs` dependencies
  (same version floors as the source `requirements.txt`), `requires-python`
  matching the source repo's Python 3.11, `[tool.uv] package = false`; check
  `infra/CLAUDE.md`'s existing conventions before adding a `ruff`/`mypy` dev
  group — only add it if those conventions call for infra lint tooling, not
  speculatively
- [ ] Run `uv lock` to generate `infra/uv.lock`, then `uv sync` to create
  `infra/.venv`
- [ ] Update `infra/stacks/__init__.py` and `infra/app.py` imports/class
  references for the renamed stacks; keep the existing stack ids
  (`{env}-kiwi-vpc-stack`, `{env}-kiwi-db-stack`) unchanged so `cdk deploy`
  targets the already-deployed CloudFormation stacks
- [ ] Verify: `cd infra && uv sync && uv run cdk synth` succeeds with no
  errors and matches the source repo's last deployed stack shape

## Network additions

- [ ] Add `alb-sg` security group to `network_stack.py`: inbound 80/443 from
  `0.0.0.0/0`, `allow_all_outbound=False`
- [ ] Add `fargate-services-sg` security group to `network_stack.py`:
  inbound all TCP from `alb-sg` only, `allow_all_outbound=True`
- [ ] Add `fargate-services-sg` as an additional inbound source (TCP 3306)
  on the existing `db-sg`
- [ ] Add an internet-facing `elbv2.ApplicationLoadBalancer` in the public
  subnets with `alb-sg`, no listener/target group yet
- [ ] Add `CfnOutput`s: `AlbArn`, `AlbDnsName`, `AlbSecurityGroupId`,
  `FargateServicesSecurityGroupId`, `PublicSubnetIds`, `PrivateSubnetIds`

## Docs

- [ ] Rewrite `infra/CLAUDE.md`: `## Setup`/`## Common Commands` sections
  updated to `uv` (`uv sync`, `uv run cdk synth`/`deploy`/`diff`/`destroy`),
  replacing the source repo's pip+venv instructions; stack layout section
  updated for `NetworkStack`/`DataStack` naming and the ALB/security-group
  additions; note `CiCdStack` exists but is not yet instantiated

## Verification & wrap-up

`cdk deploy` itself produces no repo diff, so these gate the final commit
rather than standing on their own — deploy/verify, fix forward if anything's
off, then close out the feature in the same commit.

- [ ] `uv run cdk diff --all -c env=dev` against the real dev account
  (`453542520413`/`us-east-2`) — confirm the delta is exactly the new
  ALB/security-group resources, nothing unexpected on the existing
  VPC/RDS/secrets
- [ ] `uv run cdk deploy --all -c env=dev` succeeds; confirm every
  new/existing `CfnOutput` resolves to a real resource
- [ ] Confirm no secrets/credentials/account IDs are hardcoded anywhere
  outside `cdk.json`'s non-secret context values (constitution T-4)
- [ ] Update this feature's `spec.md`/`plan.md` if anything changed during
  implementation (constitution W-1)
- [ ] Check off the `feat-03-infra-network-data` line in
  `specs/phases/roadmap.md`'s Phase 0 feature breakdown
