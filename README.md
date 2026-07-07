# Kiwi

A teaching/assessment platform: exam and assignment authoring, hosting, AI-assisted
grading, and feedback delivery for instructors and students.

## Architecture

- **identity** — synchronous Flask web service (behind an ALB). Owns auth, users,
  courses, enrollments, roles. Other services depend on it.
- **app-api** — synchronous Flask web service (behind an ALB). Owns exam authoring +
  hosting, assignment authoring, and feedback. Runs inline AI drafting
  (request/response) and enqueues grading jobs onto SQS.
- **worker** — asynchronous, SQS-driven (no ALB, no HTTP server). Polls a queue and
  runs the AI grading agents (exam + assignment grading), writing results back.
- **frontend** — Vite + React + JavaScript SPA.
- **infra** — AWS CDK (Python v2) definitions for all of the above.

Each service owns its own MySQL schema on a shared RDS instance and never reads
another service's tables. Service boundaries are defined by `contracts/`.

## Local dev quickstart

```text
make up         # start local MySQL + LocalStack (SQS/S3) via docker-compose.yml
make install    # install backend + frontend dependencies
make test       # run test suites
make down       # stop local services
```

See the `Makefile` for all available targets, including per-service Docker builds.

## Where things live

- `backend/` — the three Flask/Python services and the shared `platform_common` lib
- `frontend/` — the Vite/React/JavaScript SPA
- `infra/` — AWS CDK stacks
- `contracts/` — OpenAPI + JSON Schema contracts; source of truth for service boundaries
- `specs/` — phase roadmap and per-feature specs/plans/tasks

Agent-facing conventions live in the layered `CLAUDE.md` files (root, and one per
directory above); start with the root one.
