import os
from functools import wraps

import jwt
from flask import g, request

from platform_common.errors import ApiError


def validate_jwt(token: str) -> dict:
    """Verify signature and expiry and return the decoded claims.

    Raises ApiError(status_code=401) on any invalid, expired, or malformed
    token.
    """
    secret = os.environ["JWT_SIGNING_SECRET"]
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise ApiError("invalid or expired token", status_code=401, code="invalid_token") from exc


def require_auth(view):
    """Flask decorator that enforces a valid `Authorization: Bearer <token>`
    header, attaching the decoded claims to `flask.g.claims`."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        scheme, _, token = auth_header.partition(" ")
        if scheme != "Bearer" or not token:
            raise ApiError("missing or malformed Authorization header", status_code=401, code="invalid_token")

        g.claims = validate_jwt(token)
        return view(*args, **kwargs)

    return wrapper
