# Infra Agent Guide

Read `/constitution.md` and `../CLAUDE.md` first.

## Layout

- `app.py` — CDK app entrypoint, wires up the stacks in `stacks/`.
- `stacks/network_stack.py` — VPC, public/private subnets, ALB.
- `stacks/data_stack.py` — RDS MySQL, S3, Secrets Manager, SQS queue.
- `stacks/identity_service_stack.py` — Fargate service behind the ALB (`/auth/*`).
- `stacks/app_api_service_stack.py` — Fargate service behind the ALB (`/api/*`).
- `stacks/worker_service_stack.py` — Fargate service, SQS-driven, scales on queue
  depth, no ALB target.
- `stacks/frontend_stack.py` — S3 + CloudFront for the built SPA.

## Conventions

- AWS CDK v2, Python.
- One shared RDS instance (see `data_stack.py`); each service's schema isolation is
  enforced at the application layer (constitution P-2), not by separate instances.
- Service stacks build their container images from `backend/` as the Docker build
  context, per each service's Dockerfile.
