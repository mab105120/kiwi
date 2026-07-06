# Root Agent Guide

**Read `constitution.md` first, before making any change in this repo.** It contains
the cross-cutting rules that apply regardless of which part of the monorepo you're
working in.

## Layout

- `backend/` — three Flask microservices (`identity`, `app-api`, `worker`) plus the
  shared `platform_common` library. Has its own `CLAUDE.md`.
- `frontend/` — Vite + React + JavaScript SPA. Has its own `CLAUDE.md`.
- `infra/` — AWS CDK (Python v2) stacks. Has its own `CLAUDE.md`.
- `contracts/` — OpenAPI specs and message schemas. **These are the source of truth
  for service boundaries (see constitution P-1).**
- `specs/` — phase roadmap (`specs/phases/`) and per-feature spec/plan/tasks
  (`specs/features/<feature>/`).

Each service directory under `backend/services/<name>/` also has its own `CLAUDE.md`
with service-specific conventions — read the one nearest to the file you're editing,
in addition to this one and the constitution.

## Boundary changes

A change that crosses a service boundary (new/changed endpoint, new SQS message
shape, etc.) requires updating the relevant file in `contracts/` — and its tests —
**first**, before touching service implementation code. Contracts are the source of
truth (constitution P-1); each service owns its own MySQL schema and must never read
another service's tables (constitution P-2).

## Running things

Don't duplicate run/test instructions here — see `README.md` for the local dev
quickstart and `Makefile` for all available commands.
