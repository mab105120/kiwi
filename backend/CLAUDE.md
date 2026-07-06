# Backend Agent Guide

Read `/constitution.md` first, then `../CLAUDE.md`, before making changes here.

## Layout

- `libs/platform_common/` — shared library (auth helpers, error envelope, logging)
  used by all three services via a path dependency.
- `services/identity/` — synchronous Flask web service, behind an ALB.
- `services/app-api/` — synchronous Flask web service, behind an ALB.
- `services/worker/` — asynchronous SQS-driven worker, no HTTP server.

Each service has its own `CLAUDE.md` with service-specific conventions.

## Conventions

- Python 3.12. Dependency management via `uv`; `pyproject.toml` at this level is a
  workspace referencing `libs/` and all three `services/`.
- Each service owns its own MySQL schema on the shared RDS instance (constitution
  P-2) — never import another service's models or query its tables directly.
- Request/response shapes must match `contracts/<service>.openapi.yaml`
  (constitution P-1). `worker` message shapes must match
  `contracts/messages/grading-job.schema.json`.
- Service Dockerfiles are built with `backend/` as the build context (see each
  Dockerfile's header comment) so they can install `libs/platform_common`.
