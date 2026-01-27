import pytest

from app.service.cognito_client import CognitoClientError, get_user_info


def test_get_user_info_success(app, monkeypatch):
    def mock_post(*args, **kwargs):
        class MockResponse:
            def json(self):
                return {
                    'Username': 'test_user',
                    'UserAttributes': [
                        {'Name': 'email', 'Value': 'test@example.com'},
                        {'Name': 'given_name', 'Value': 'Test'},
                        {'Name': 'family_name', 'Value': 'User'},
                    ],
                }

        return MockResponse()

    monkeypatch.setattr('app.service.cognito_client.requests.post', mock_post)

    result = get_user_info('mock_access_token')

    assert result['username'] == 'test_user'
    assert result['attributes']['email'] == 'test@example.com'
    assert result['attributes']['given_name'] == 'Test'
    assert result['attributes']['family_name'] == 'User'


def test_get_user_info_error(app, monkeypatch):
    def mock_post(*args, **kwargs):
        raise Exception('Connection error')

    monkeypatch.setattr('app.service.cognito_client.requests.post', mock_post)

    with pytest.raises(CognitoClientError) as exc_info:
        get_user_info('mock_access_token')
    assert 'Failed to fetch user info due to error' in str(exc_info.value)
    assert 'Connection error' in str(exc_info.value)


def test_get_user_info_empty_attributes(app, monkeypatch):
    def mock_post(*args, **kwargs):
        class MockResponse:
            def json(self):
                return {
                    'Username': 'minimal_user',
                    'UserAttributes': [],
                }

        return MockResponse()

    monkeypatch.setattr('app.service.cognito_client.requests.post', mock_post)

    result = get_user_info('mock_access_token')

    assert result['username'] == 'minimal_user'
    assert result['attributes'] == {}


def test_get_user_info_multiple_attributes(app, monkeypatch):
    def mock_post(*args, **kwargs):
        class MockResponse:
            def json(self):
                return {
                    'Username': 'complex_user',
                    'UserAttributes': [
                        {'Name': 'sub', 'Value': '12345-67890'},
                        {'Name': 'email', 'Value': 'complex@example.com'},
                        {'Name': 'email_verified', 'Value': 'true'},
                        {'Name': 'phone_number', 'Value': '+1234567890'},
                        {'Name': 'phone_number_verified', 'Value': 'false'},
                        {'Name': 'given_name', 'Value': 'Complex'},
                        {'Name': 'family_name', 'Value': 'User'},
                        {'Name': 'custom:role', 'Value': 'admin'},
                    ],
                }

        return MockResponse()

    monkeypatch.setattr('app.service.cognito_client.requests.post', mock_post)

    result = get_user_info('mock_access_token')

    assert result['username'] == 'complex_user'
    assert result['attributes']['sub'] == '12345-67890'
    assert result['attributes']['email'] == 'complex@example.com'
    assert result['attributes']['email_verified'] == 'true'
    assert result['attributes']['phone_number'] == '+1234567890'
    assert result['attributes']['custom:role'] == 'admin'
