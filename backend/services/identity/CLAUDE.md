# identity Agent Guide

Read `../../../CLAUDE.md` and `/constitution.md` first.

## What this service owns

Auth, users, courses, enrollments, roles. Other services depend on this one, but
never on its database directly — they must go through its API. Its contract is
`contracts/identity.openapi.yaml`.

## Conventions

- Synchronous Flask app behind an ALB, served by `gunicorn` in the container.
- Owns its own MySQL schema exclusively (constitution P-2); migrations live in
  `migrations/` (Alembic).
- Any change to the API surface requires updating `contracts/identity.openapi.yaml`
  and `tests/contract/` first (constitution P-1).
