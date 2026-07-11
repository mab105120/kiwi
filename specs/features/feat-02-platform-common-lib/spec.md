# Spec: Platform Common Library

## Why

Phase 0 (`specs/phases/roadmap.md`) requires `identity`, `app-api`, and `worker`
to share auth verification, error handling, and logging so behavior is
consistent across service boundaries instead of each service inventing its
own. `backend/libs/platform_common/platform_common/{auth,errors,logging}.py`
currently exist only as stubs (`validate_jwt` and `configure_logging` raise
`NotImplementedError`; `ApiError` has no way to actually reach a Flask
response). No service can enforce auth on a route, return a consistent error
body, or emit structured logs without this landing first.

## Scope

- **JWT verification** (`platform_common/auth.py`):
  - `validate_jwt(token: str) -> dict` verifies signature and expiry and
    returns the decoded claims, raising `ApiError(status_code=401)` on any
    invalid, expired, or malformed token.
  - Signing key material is read from an environment variable (e.g.
    `JWT_SIGNING_SECRET`), not hardcoded — this is a placeholder seam for
    `identity` to become the actual issuer once Phase 1 builds real auth;
    no Secrets Manager integration yet (that's `feat-03`/`feat-05`).
  - A `require_auth` Flask decorator that reads the `Authorization: Bearer
    <token>` header, calls `validate_jwt`, attaches the resulting claims to
    `flask.g`, and short-circuits with a 401 error envelope on failure — this
    is the actual integration point `identity`/`app-api`/`worker`'s HTTP
    routes will use to protect endpoints in later phases.
- **Shared error envelope** (`platform_common/errors.py`):
  - Keep the existing `ApiError` shape (`{"error": {"message", "code"}}`).
  - Add `register_error_handlers(app: Flask) -> None`, which each service
    calls once from its `create_app()`, that maps `ApiError` to its
    `status_code`/`to_dict()` JSON body, and maps any other uncaught
    exception to a generic `500` envelope that never leaks a stack trace or
    exception message to the client (S-5).
- **Structured logging with PII redaction** (`platform_common/logging.py`):
  - `configure_logging() -> None` sets up JSON-structured logging to stdout
    (timestamp, level, logger name, message, plus service name) shared by
    all three services.
  - A redaction layer (logging filter/formatter) strips or masks known
    sensitive fields/patterns before a record is emitted — at minimum email
    addresses, bearer tokens/JWTs, and any field literally named
    `password`/`token`/`answer` — so no log line can ever contain PII, a
    secret, or student answer content (S-5, constitution `## Phase 0` bullet
    on `platform_common`).
- Wire all three services (`identity`, `app-api`, `worker`) to call
  `configure_logging()` and `register_error_handlers(app)` (the latter for
  the two Flask services only) from their `create_app()`/startup path, so
  the library is actually in use, not just implemented.
- Add `backend/libs/platform_common/tests/unit/` with real unit tests for
  all three modules (valid/expired/bad-signature JWTs, redaction filter,
  error-handler status/body mapping) — `make test-backend` already runs
  pytest per workspace member, so this only needs test files, not tooling
  changes.

## Out of scope

- Wiring `contracts/*.openapi.yaml` error response schemas to formally
  reference this envelope shape. `contracts/app-api/openapi.yml` and
  `contracts/identity.openapi.yaml` currently only describe `/healthz` (plus
  a TODO `/auth/token` stub) — there's no real endpoint yet to bind an error
  schema to. Deferred to whichever feature first specs a real endpoint
  (Phase 1 `identity`, Phase 2 `exams`).
- `identity` actually issuing JWTs (`POST /auth/token`) — this feature only
  builds the shared *verification* side. Issuing is Phase 1 (`identity`
  service) work.
- Any route in `identity`/`app-api`/`worker` actually calling `require_auth`
  on a real business endpoint — none exist yet outside `/healthz`.
- Secrets Manager / KMS-backed key material (`feat-03-infra-network-data`,
  `feat-05-infra-service-shells`) — local/CI dev uses an env var.
- Request-id/correlation-id propagation across services — nothing emits or
  forwards one yet; can be layered onto the logging setup in a later
  feature once there's a real request path to trace.

## Acceptance criteria

- [ ] `validate_jwt` accepts a validly-signed, unexpired token and returns
  its claims; rejects an expired token, a token signed with the wrong key,
  and a malformed token, each raising `ApiError` with `status_code == 401`.
- [ ] A Flask route decorated with `require_auth` returns a `401` JSON error
  envelope for a missing/invalid/expired `Authorization` header, and calls
  through to the handler (with claims available on `flask.g`) for a valid
  one.
- [ ] `register_error_handlers` makes a Flask app return the `ApiError`
  envelope with the correct status code for a raised `ApiError`, and a
  generic `500` envelope (no stack trace, no exception message) for any
  other uncaught exception.
- [ ] `configure_logging` produces structured (JSON) log lines on stdout,
  and a log call containing an email address, a bearer token, or a field
  named `password`/`token`/`answer` never emits that value verbatim (S-5).
- [ ] `identity`, `app-api`, and `worker` each call `configure_logging()` on
  startup; `identity` and `app-api` each call `register_error_handlers`
  from `create_app()`.
- [ ] `make test-backend` collects and passes new unit tests for all three
  `platform_common` modules.
- [ ] No secrets or credentials introduced anywhere in this change
  (constitution T-4) — the JWT signing secret is read from an env var, never
  committed.
