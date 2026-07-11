import datetime

import jwt
import pytest
from flask import Flask, g, jsonify

from platform_common.auth import require_auth, validate_jwt
from platform_common.errors import ApiError, register_error_handlers

SECRET = "test-signing-secret-at-least-32-bytes-long"


@pytest.fixture(autouse=True)
def signing_secret(monkeypatch):
    monkeypatch.setenv("JWT_SIGNING_SECRET", SECRET)


def _make_token(secret: str = SECRET, expires_delta: datetime.timedelta = datetime.timedelta(minutes=5)):
    claims = {
        "sub": "user-1",
        "exp": datetime.datetime.now(datetime.timezone.utc) + expires_delta,
    }
    return jwt.encode(claims, secret, algorithm="HS256")


def test_validate_jwt_accepts_a_valid_token():
    token = _make_token()

    claims = validate_jwt(token)

    assert claims["sub"] == "user-1"


def test_validate_jwt_rejects_expired_token():
    token = _make_token(expires_delta=datetime.timedelta(minutes=-5))

    with pytest.raises(ApiError) as exc_info:
        validate_jwt(token)

    assert exc_info.value.status_code == 401


def test_validate_jwt_rejects_wrong_signing_key():
    token = _make_token(secret="a-different-secret")

    with pytest.raises(ApiError) as exc_info:
        validate_jwt(token)

    assert exc_info.value.status_code == 401


def test_validate_jwt_rejects_malformed_token():
    with pytest.raises(ApiError) as exc_info:
        validate_jwt("not-a-jwt")

    assert exc_info.value.status_code == 401


@pytest.fixture
def protected_client():
    app = Flask(__name__)
    register_error_handlers(app)

    @app.get("/protected")
    @require_auth
    def protected():
        return jsonify(sub=g.claims["sub"])

    return app.test_client()


def test_require_auth_rejects_missing_header(protected_client):
    response = protected_client.get("/protected")

    assert response.status_code == 401


def test_require_auth_rejects_malformed_header(protected_client):
    response = protected_client.get("/protected", headers={"Authorization": "garbled"})

    assert response.status_code == 401


def test_require_auth_rejects_invalid_token(protected_client):
    response = protected_client.get(
        "/protected", headers={"Authorization": "Bearer not-a-jwt"}
    )

    assert response.status_code == 401


def test_require_auth_calls_through_with_claims_on_valid_token(protected_client):
    token = _make_token()

    response = protected_client.get(
        "/protected", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.get_json() == {"sub": "user-1"}
