# Frontend Agent Guide

Read `/constitution.md` and `../CLAUDE.md` first.

## Layout

- `src/api/` — generated API clients from `contracts/*.openapi.yaml` (`make client`).
  Don't hand-edit generated clients.
- `src/components/` — shared, reusable UI components.
- `src/routes/` — top-level route definitions.
- `src/lib/` — framework-agnostic utilities.
- `src/features/` — one directory per feature area: `exam-authoring`,
  `exam-taking`, `grading-review`, `assignments`.

## Conventions

- Vite + React + JavaScript (no TypeScript).
- The frontend talks to `identity` and `app-api` only via their OpenAPI contracts
  in `contracts/` — never assume an endpoint that isn't in those files
  (constitution P-1).
