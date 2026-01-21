import pytest
import requests
from flask import g, jsonify
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError

from app.auth import CognitoTokenValidator, get_token_from_header, requires_auth


def test_get_token_missing_authorization_header(app):
    with app.test_request_context(headers={}):
        result = get_token_from_header()
        assert result is None


def test_get_token_empty_authorization_header(app):
    with app.test_request_context(headers={'Authorization': ''}):
        result = get_token_from_header()
        assert result is None


def test_get_token_without_bearer_prefix(app):
    with app.test_request_context(headers={'Authorization': 'Basic abc123'}):
        result = get_token_from_header()
        assert result is None


def test_get_token_bearer_only_no_token(app):
    with app.test_request_context(headers={'Authorization': 'Bearer'}):
        result = get_token_from_header()
        assert result is None


def test_get_token_too_many_parts(app):
    with app.test_request_context(headers={'Authorization': 'Bearer token extra'}):
        result = get_token_from_header()
        assert result is None


def test_get_token_valid_bearer_token(app):
    with app.test_request_context(headers={'Authorization': 'Bearer my-valid-token'}):
        result = get_token_from_header()
        assert result == 'my-valid-token'


def test_get_token_with_jwt_format(app):
    token = (
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U'
    )
    with app.test_request_context(headers={'Authorization': f'Bearer {token}'}):
        result = get_token_from_header()
        assert result == token


def test_get_jwks_first_call_fetches_from_url(monkeypatch):
    call_count = {'count': 0}
    mock_jwks = {'keys': [{'kid': 'key1', 'n': 'modulus'}]}

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return mock_jwks

    def mock_get(url):
        call_count['count'] += 1
        return MockResponse()

    monkeypatch.setattr(requests, 'get', mock_get)

    validator = CognitoTokenValidator(region='us-east-1', user_pool_id='pool123', app_client_id='client123')
    result = validator._get_jwks()

    assert result == mock_jwks
    assert call_count['count'] == 1


def test_get_jwks_subsequent_calls_use_cache(monkeypatch):
    call_count = {'count': 0}
    mock_jwks = {'keys': [{'kid': 'key1', 'n': 'modulus'}]}

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return mock_jwks

    def mock_get(url):
        call_count['count'] += 1
        return MockResponse()

    monkeypatch.setattr(requests, 'get', mock_get)

    validator = CognitoTokenValidator(region='us-east-1', user_pool_id='pool123', app_client_id='client123')
    result1 = validator._get_jwks()
    result2 = validator._get_jwks()
    result3 = validator._get_jwks()

    assert result1 == mock_jwks
    assert result2 == mock_jwks
    assert result3 == mock_jwks
    assert call_count['count'] == 1


def test_get_jwks_network_error_raises(monkeypatch):
    def mock_get(url):
        raise requests.exceptions.ConnectionError('Network error')

    monkeypatch.setattr(requests, 'get', mock_get)

    validator = CognitoTokenValidator(region='us-east-1', user_pool_id='pool123', app_client_id='client123')

    with pytest.raises(requests.exceptions.ConnectionError, match='Network error'):
        validator._get_jwks()


def test_get_jwks_http_error_raises(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            raise requests.exceptions.HTTPError('404 Not Found')

        def json(self):
            return {}

    def mock_get(url):
        return MockResponse()

    monkeypatch.setattr(requests, 'get', mock_get)

    validator = CognitoTokenValidator(region='us-east-1', user_pool_id='pool123', app_client_id='client123')

    with pytest.raises(requests.exceptions.HTTPError, match='404 Not Found'):
        validator._get_jwks()


def test_get_signing_key_missing_kid(monkeypatch):
    def mock_get_unverified_header(token):
        return {'alg': 'RS256'}

    monkeypatch.setattr(jwt, 'get_unverified_header', mock_get_unverified_header)

    validator = CognitoTokenValidator(region='us-east-1', user_pool_id='pool123', app_client_id='client123')
    result = validator._get_signing_key('fake-token')

    assert result is None


def test_get_signing_key_no_matching_key_in_jwks(monkeypatch):
    def mock_get_unverified_header(token):
        return {'kid': 'key-not-found', 'alg': 'RS256'}

    def mock_get_jwks(self):
        return {'keys': [{'kid': 'key1', 'n': 'modulus1'}, {'kid': 'key2', 'n': 'modulus2'}]}

    monkeypatch.setattr(jwt, 'get_unverified_header', mock_get_unverified_header)
    monkeypatch.setattr(CognitoTokenValidator, '_get_jwks', mock_get_jwks)

    validator = CognitoTokenValidator(region='us-east-1', user_pool_id='pool123', app_client_id='client123')
    result = validator._get_signing_key('fake-token')

    assert result is None


def test_get_signing_key_invalid_jwt_format(monkeypatch):
    def mock_get_unverified_header(token):
        raise JWTError('Invalid token format')

    monkeypatch.setattr(jwt, 'get_unverified_header', mock_get_unverified_header)

    validator = CognitoTokenValidator(region='us-east-1', user_pool_id='pool123', app_client_id='client123')
    result = validator._get_signing_key('invalid-token')

    assert result is None


def test_get_signing_key_valid_token_with_matching_key(monkeypatch):
    def mock_get_unverified_header(token):
        return {'kid': 'matching-key', 'alg': 'RS256'}

    def mock_get_jwks(self):
        return {
            'keys': [
                {'kid': 'key1', 'n': 'modulus1'},
                {'kid': 'matching-key', 'n': 'modulus2', 'e': 'exponent'},
                {'kid': 'key3', 'n': 'modulus3'},
            ]
        }

    monkeypatch.setattr(jwt, 'get_unverified_header', mock_get_unverified_header)
    monkeypatch.setattr(CognitoTokenValidator, '_get_jwks', mock_get_jwks)

    validator = CognitoTokenValidator(region='us-east-1', user_pool_id='pool123', app_client_id='client123')
    result = validator._get_signing_key('fake-token')

    assert result == {'kid': 'matching-key', 'n': 'modulus2', 'e': 'exponent'}


def test_validate_token_no_signing_key(monkeypatch):
    def mock_get_signing_key(self, token):
        return None

    monkeypatch.setattr(CognitoTokenValidator, '_get_signing_key', mock_get_signing_key)

    validator = CognitoTokenValidator(region='us-east-1', user_pool_id='pool123', app_client_id='client123')

    with pytest.raises(Exception, match='Unable to find matching signing key'):
        validator.validate_token('fake-token')


def test_validate_token_expired(monkeypatch):
    def mock_get_signing_key(self, token):
        return {'kid': 'key1', 'n': 'modulus'}

    def mock_jwt_decode(token, key, algorithms, audience, issuer, options):
        raise ExpiredSignatureError('Signature has expired')

    monkeypatch.setattr(CognitoTokenValidator, '_get_signing_key', mock_get_signing_key)
    monkeypatch.setattr(jwt, 'decode', mock_jwt_decode)

    validator = CognitoTokenValidator(region='us-east-1', user_pool_id='pool123', app_client_id='client123')

    with pytest.raises(Exception, match='Token has expired'):
        validator.validate_token('expired-token')


def test_validate_token_invalid_claims(monkeypatch):
    def mock_get_signing_key(self, token):
        return {'kid': 'key1', 'n': 'modulus'}

    def mock_jwt_decode(token, key, algorithms, audience, issuer, options):
        raise JWTClaimsError('Invalid audience')

    monkeypatch.setattr(CognitoTokenValidator, '_get_signing_key', mock_get_signing_key)
    monkeypatch.setattr(jwt, 'decode', mock_jwt_decode)

    validator = CognitoTokenValidator(region='us-east-1', user_pool_id='pool123', app_client_id='client123')

    with pytest.raises(Exception, match='Invalid token claims'):
        validator.validate_token('invalid-claims-token')


def test_validate_token_jwt_error(monkeypatch):
    def mock_get_signing_key(self, token):
        return {'kid': 'key1', 'n': 'modulus'}

    def mock_jwt_decode(token, key, algorithms, audience, issuer, options):
        raise JWTError('Token validation failed')

    monkeypatch.setattr(CognitoTokenValidator, '_get_signing_key', mock_get_signing_key)
    monkeypatch.setattr(jwt, 'decode', mock_jwt_decode)

    validator = CognitoTokenValidator(region='us-east-1', user_pool_id='pool123', app_client_id='client123')

    with pytest.raises(Exception, match='Token validation failed'):
        validator.validate_token('malformed-token')


def test_validate_token_missing_token_use(monkeypatch):
    def mock_get_signing_key(self, token):
        return {'kid': 'key1', 'n': 'modulus'}

    def mock_jwt_decode(token, key, algorithms, audience, issuer, options):
        return {'sub': 'user123', 'username': 'testuser', 'exp': 9999999999}

    monkeypatch.setattr(CognitoTokenValidator, '_get_signing_key', mock_get_signing_key)
    monkeypatch.setattr(jwt, 'decode', mock_jwt_decode)

    validator = CognitoTokenValidator(region='us-east-1', user_pool_id='pool123', app_client_id='client123')

    with pytest.raises(Exception, match='Invalid token_use: None'):
        validator.validate_token('token-without-use')


def test_validate_token_wrong_token_use(monkeypatch):
    def mock_get_signing_key(self, token):
        return {'kid': 'key1', 'n': 'modulus'}

    def mock_jwt_decode(token, key, algorithms, audience, issuer, options):
        return {'sub': 'user123', 'username': 'testuser', 'exp': 9999999999, 'token_use': 'id'}

    monkeypatch.setattr(CognitoTokenValidator, '_get_signing_key', mock_get_signing_key)
    monkeypatch.setattr(jwt, 'decode', mock_jwt_decode)

    validator = CognitoTokenValidator(region='us-east-1', user_pool_id='pool123', app_client_id='client123')

    with pytest.raises(Exception, match='Invalid token_use: id'):
        validator.validate_token('id-token')


def test_validate_token_valid(monkeypatch):
    def mock_get_signing_key(self, token):
        return {'kid': 'key1', 'n': 'modulus'}

    def mock_jwt_decode(token, key, algorithms, audience, issuer, options):
        return {
            'sub': 'user123',
            'username': 'testuser',
            'email': 'test@example.com',
            'exp': 9999999999,
            'token_use': 'access',
        }

    monkeypatch.setattr(CognitoTokenValidator, '_get_signing_key', mock_get_signing_key)
    monkeypatch.setattr(jwt, 'decode', mock_jwt_decode)

    validator = CognitoTokenValidator(region='us-east-1', user_pool_id='pool123', app_client_id='client123')
    result = validator.validate_token('valid-token')

    assert result == {
        'sub': 'user123',
        'username': 'testuser',
        'email': 'test@example.com',
        'exp': 9999999999,
        'token_use': 'access',
    }


def test_requires_auth_no_token(app, monkeypatch):
    monkeypatch.setattr('app.auth.get_token_from_header', lambda: None)

    @requires_auth
    def protected_route():
        return jsonify({'message': 'success'}), 401

    with app.test_request_context('/protected', headers={}):
        response = protected_route()
        assert response[1] == 401
        data = response[0].get_json()
        assert 'error' in data
        assert data['error'] == 'Missing authorization token'
        assert data['message'] == 'Authorization header with Bearer token required'


def test_requires_auth_no_validator_in_config(app, monkeypatch):
    monkeypatch.setattr('app.auth.get_token_from_header', lambda: 'Bearer token123')
    original_validator = app.config.get('COGNITO_VALIDATOR')
    app.config['COGNITO_VALIDATOR'] = None

    @requires_auth
    def protected_route():
        return jsonify({'message': 'success'}), 500

    with app.test_request_context('/protected'):
        response = protected_route()
        assert response[1] == 500
        data = response[0].get_json()
        assert 'error' in data
        assert data['error'] == 'Server configuration error'

    app.config['COGNITO_VALIDATOR'] = original_validator


def test_requires_auth_invalid_token(app, monkeypatch):
    monkeypatch.setattr('app.auth.get_token_from_header', lambda: 'Bearer bad-token')
    validator = CognitoTokenValidator(region='us-east-1', user_pool_id='pool123', app_client_id='client123')
    original_validator = app.config.get('COGNITO_VALIDATOR')
    app.config['COGNITO_VALIDATOR'] = validator

    def mock_validate_token(token):
        raise Exception('Invalid signature')

    monkeypatch.setattr(validator, 'validate_token', mock_validate_token)

    @requires_auth
    def protected_route():
        return jsonify({'message': 'success'}), 401

    with app.test_request_context('/protected'):
        response = protected_route()
        assert response[1] == 401
        data = response[0].get_json()
        assert 'error' in data
        assert data['error'] == 'Invalid token'
        assert 'Invalid signature' in data['message']

    app.config['COGNITO_VALIDATOR'] = original_validator


def test_requires_auth_valid_token(app, monkeypatch):
    @requires_auth
    def protected_route():
        return jsonify(
            {
                'message': 'success',
                'user_id': g.user['user_id'],
                'username': g.user['username'],
                'email': g.user['email'],
            }
        )

    with app.test_request_context('/protected'):
        response = protected_route()
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'success'
        assert data['user_id'] == 'user-abc'
        assert data['username'] == 'test_user'
        assert data['email'] == 'test@test.com'


def test_requires_auth_populates_g_user_with_all_fields(app, monkeypatch):
    @requires_auth
    def protected_route():
        assert 'user' in g
        assert g.user['user_id'] == 'user-abc'
        assert g.user['username'] == 'test_user'
        assert g.user['email'] == 'test@test.com'
        assert g.user['token_expiry'] == 1234567890
        return jsonify({'message': 'verified'}), 200

    with app.test_request_context('/protected'):
        response = protected_route()
        assert response[1] == 200
