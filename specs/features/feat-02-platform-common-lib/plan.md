# Plan: Platform Common Library

## Approach

Implement the three `platform_common` modules independently (they don't
depend on each other), then wire all three services to actually call them,
then add unit tests. `errors.py` goes first since `auth.py`'s `require_auth`
needs `ApiError` to already raise a shaped response.

**`errors.py`**

- Keep `ApiError` as-is (already matches the envelope shape).
- Add `register_error_handlers(app)`: an `@app.errorhandler(ApiError)` that
  returns `(err.to_dict(), err.status_code)`, plus an
  `@app.errorhandler(Exception)` catch-all that logs the real exception
  (via the `logging` module, server-side only) and returns a fixed generic
  `{"error": {"message": "internal server error", "code": "internal_error"}}`,
  `500` — so nothing exception-specific ever reaches the client (S-5).

**`auth.py`**

- Use `PyJWT` (add as a `platform_common` dependency) for encode/decode.
- `validate_jwt(token)`: `jwt.decode(token, secret, algorithms=["HS256"])`,
  reading `secret` from `os.environ["JWT_SIGNING_SECRET"]` at call time (not
  module import time, so tests can set/unset it per-case). Catch
  `jwt.PyJWTError` (covers expired/bad-signature/malformed) and re-raise as
  `ApiError(status_code=401, code="invalid_token")`.
- `require_auth`: a decorator that reads `request.headers["Authorization"]`,
  splits on `Bearer `, 401s via `ApiError` if missing/malformed, else calls
  `validate_jwt` and stores claims on `flask.g.claims` before calling the
  wrapped view.

**`logging.py`**

- Use stdlib `logging` + `logging.Formatter` subclass (or a small dependency
  like `python-json-logger` if it doesn't fight the workspace's dependency
  pinning — decide during implementation, default to hand-rolled
  `JSONFormatter` if adding a dependency is more friction than it's worth) to
  emit one JSON object per line: `timestamp`, `level`, `logger`, `message`,
  `service` (from an env var or param).
- Redaction: a `logging.Filter` that walks the record's message/args and
  masks values for known sensitive key names (`password`, `token`, `answer`,
  `email`) if the log call passes structured `extra=` fields, and
  regex-masks bearer-token-shaped and email-shaped substrings in the
  rendered message string itself, since callers won't always pass structured
  fields. Document in the module that this is best-effort pattern matching,
  not a guarantee — callers still must not log raw PII deliberately.
- `configure_logging()` installs the JSON formatter + redaction filter on
  the root logger's stdout handler; idempotent (safe to call more than
  once, e.g. under `gunicorn` + Flask reload).

**Service wiring**

- `identity/app/__init__.py` and `app-api/app/__init__.py`: call
  `configure_logging()` and `register_error_handlers(app)` in `create_app()`,
  before the `/healthz` route.
- `worker/app/worker.py`: call `configure_logging()` at process start (no
  Flask app / error handlers there — it's SQS-driven).

**Dependency wiring**

- Add `PyJWT` to `backend/libs/platform_common/pyproject.toml`.
- Each service's `pyproject.toml` already depends on `platform-common` via
  `tool.uv.sources` path dependency (per `feat-01`) — `uv sync` picks up the
  new transitive dependency automatically, no per-service change needed.

**Tests**

- `backend/libs/platform_common/tests/unit/` (new): `test_auth.py` (valid
  token, expired token, wrong-secret token, malformed token, missing/garbled
  `Authorization` header via a minimal Flask test app),
  `test_errors.py` (`ApiError` → response shape/status,  uncaught exception →
  generic 500), `test_logging.py` (log output is valid JSON, sensitive
  fields/patterns don't appear verbatim in the emitted line).
- `platform_common` was already a `backend/pyproject.toml` workspace member
  (`feat-01`) and picks up `pytest` from the workspace root's
  `[dependency-groups] dev` — no per-package dev dependency needed, only the
  new test files.

## Risks

- `identity` doesn't issue real JWTs yet (Phase 1), so `validate_jwt`/
  `require_auth` can only be verified against hand-crafted test tokens
  signed with the same env-var secret, not an actual end-to-end login flow.
  That's expected for this feature — full integration is a Phase 1 concern.
- Symmetric (`HS256`, shared-secret) signing is a deliberate placeholder.
  Real inter-service verification without a shared DB (P-2) or a live call
  to `identity` per-request (P-4, latency) will likely want asymmetric
  (`RS256`) signing with `identity` holding the private key and other
  services verifying with a public key/JWKS — revisit when Phase 1 makes
  `identity` a real issuer and Secrets Manager (`feat-03`) exists to
  distribute the key material.
- Regex/key-name-based log redaction is inherently best-effort — it cannot
  guarantee every possible PII shape is caught. Flag this limitation in the
  module docstring rather than overclaiming S-5 compliance from this layer
  alone; callers remain responsible for not logging raw sensitive payloads.
- Confirmed `make test-backend`'s pytest invocation (from `feat-01`) only
  listed `services/*` explicitly, not `platform_common` — added
  `libs/platform_common` to that list in the root `Makefile`.

## Sequencing

1. `errors.py`: add `register_error_handlers`.
2. `auth.py`: add `PyJWT` dependency, implement `validate_jwt` +
   `require_auth`.
3. `logging.py`: implement `configure_logging` (JSON formatter + redaction
   filter).
4. Wire `identity`, `app-api`, `worker` to call the above from their
   startup paths.
5. Add `backend/libs/platform_common/tests/unit/` covering all three
   modules; confirm/fix `make test-backend` picks them up.
6. Verify all acceptance criteria end-to-end via `make test-backend` +
   `make lint-backend`.
