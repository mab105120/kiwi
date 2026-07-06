# worker Agent Guide

Read `../../../CLAUDE.md` and `/constitution.md` first.

## What this service owns

Asynchronous, SQS-driven AI grading (exam + assignment). No ALB, no HTTP server —
it polls the grading-job queue that `app-api` enqueues onto and writes results
back to its own database. Its boundary contract is
`contracts/messages/grading-job.schema.json` (it has no OpenAPI file since it has
no HTTP API).

## Conventions

- Entry point is `app/worker.py`'s poll loop, run via `python -m app.worker` (not
  gunicorn — there is no web server here).
- Owns its own MySQL schema exclusively (constitution P-2) — the grades/feedback
  tables; migrations live in `migrations/` (Alembic).
- Any change to the consumed message shape requires updating
  `contracts/messages/grading-job.schema.json` and `tests/contract/` first
  (constitution P-1), since `app-api` produces messages against that same schema.
