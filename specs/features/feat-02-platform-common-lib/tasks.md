# Tasks: Platform Common Library

## Errors

- [ ] Add `register_error_handlers(app)` to `errors.py`: `ApiError` →
  `to_dict()`/`status_code`; any other exception → generic `500` envelope
  with no leaked exception detail

## Auth

- [ ] Add `PyJWT` dependency to `backend/libs/platform_common/pyproject.toml`
- [ ] Implement `validate_jwt(token)`: decode + verify signature/expiry via
  `JWT_SIGNING_SECRET` env var, raise `ApiError(401)` on any failure
- [ ] Add `require_auth` Flask decorator: parse `Authorization: Bearer`
  header, call `validate_jwt`, attach claims to `flask.g`, 401 on failure

## Logging

- [ ] Implement `configure_logging()`: JSON-structured stdout logging
  (timestamp, level, logger, message, service name)
- [ ] Add redaction filter/formatter: mask known sensitive field names
  (`password`, `token`, `answer`, `email`) and bearer-token/email-shaped
  substrings in rendered messages (S-5)
- [ ] Make `configure_logging()` idempotent (safe under gunicorn/reload)

## Service wiring

- [ ] `identity/app/__init__.py`: call `configure_logging()` +
  `register_error_handlers(app)` in `create_app()`
- [ ] `app-api/app/__init__.py`: call `configure_logging()` +
  `register_error_handlers(app)` in `create_app()`
- [ ] `worker/app/worker.py`: call `configure_logging()` at process start

## Tests

- [ ] Add `backend/libs/platform_common/tests/unit/test_auth.py`: valid
  token, expired token, wrong-secret token, malformed token,
  missing/malformed `Authorization` header
- [ ] Add `backend/libs/platform_common/tests/unit/test_errors.py`:
  `ApiError` → correct status/body; uncaught exception → generic 500
- [ ] Add `backend/libs/platform_common/tests/unit/test_logging.py`: output
  is valid JSON; sensitive fields/patterns never appear verbatim
- [ ] Confirm `make test-backend` runs `platform_common`'s tests (add it to
  the per-package pytest loop if it's currently only `services/*`)
- [ ] Verify: `make lint-backend` and `make test-backend` both pass clean

## Wrap-up

- [ ] Update this feature's `spec.md`/`plan.md` if anything changed during
  implementation (constitution W-1)
- [ ] Check off the `feat-02-platform-common-lib` line in
  `specs/phases/roadmap.md`'s Phase 0 feature breakdown
