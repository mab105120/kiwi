# Contracts

This directory is the source of truth for service boundaries (constitution P-1).

- `identity.openapi.yaml` — OpenAPI 3.1 contract for the `identity` service.
- `app-api.openapi.yaml` — OpenAPI 3.1 contract for the `app-api` service.
- `messages/grading-job.schema.json` — JSON Schema for the SQS grading-job message
  that `app-api` produces and `worker` consumes. `worker` has no HTTP API, so this
  schema is its boundary contract instead of an OpenAPI file.

## Generating clients/stubs

TODO: wire up codegen so that:
- `frontend/src/api/` clients are generated from `identity.openapi.yaml` and
  `app-api.openapi.yaml` (see `make client`).
- Each backend service's `tests/contract/` validates its implementation against its
  own OpenAPI file (or, for `worker`, against `messages/grading-job.schema.json`).

Any boundary change must update the relevant file here, and its tests, before
implementation code changes.
