# app-api Agent Guide

Read `../../../CLAUDE.md` and `/constitution.md` first.

## What this service owns

Exam authoring + hosting, assignment authoring, and feedback. Runs inline AI
question-drafting synchronously (request/response, see `app/agents/`). Enqueues
grading jobs onto SQS for `worker` to consume — the message shape is defined in
`contracts/messages/grading-job.schema.json`, not an OpenAPI file. Its own HTTP
contract is `contracts/app-api.openapi.yaml`.

## Conventions

- Synchronous Flask app behind an ALB, served by `gunicorn` in the container.
- Owns its own MySQL schema exclusively (constitution P-2); migrations live in
  `migrations/` (Alembic).
- Any change to the API surface requires updating `contracts/app-api.openapi.yaml`
  and `tests/contract/` first (constitution P-1). Any change to the grading job
  message shape requires updating `contracts/messages/grading-job.schema.json`
  first, since `worker` depends on it.
