import datetime

import app.service.transaction_service as transaction_service
import app.service.user_service as user_service
from app.models import Transaction, User


def test_get_all_users(client, monkeypatch):
    # Mock service to return list of users
    mock_users = [
        User(
            username='user1',
            firstname='First',
            lastname='Last',
            balance=100.0,
        ),
        User(
            username='user2',
            firstname='Second',
            lastname='User',
            balance=200.0,
        ),
    ]
    monkeypatch.setattr(user_service, 'get_all_users', lambda: mock_users)

    response = client.get('/users/')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_get_user_success(client, monkeypatch):
    # Mock service to return a user
    mock_user = User(
        username='testuser',
        firstname='Test',
        lastname='User',
        balance=100.0,
    )
    monkeypatch.setattr(user_service, 'get_user_by_username', lambda _: mock_user)

    response = client.get('/users/testuser')
    assert response.status_code == 200
    data = response.get_json()
    assert data['username'] == 'testuser'
    assert 'firstname' in data
    assert 'lastname' in data
    assert 'balance' in data


def test_get_user_not_found(client, monkeypatch):
    # Mock service to return None
    monkeypatch.setattr(user_service, 'get_user_by_username', lambda _: None)

    response = client.get('/users/nonexistent_user_xyz')
    assert response.status_code == 404
    data = response.get_json()
    assert 'error_msg' in data


def test_create_user_success(client, monkeypatch):
    monkeypatch.setattr(user_service, 'create_user', lambda **_: None)

    new_user = {
        'username': 'testuser1',
        'firstname': 'Test',
        'lastname': 'User',
    }
    response = client.post('/users/', json=new_user)
    assert response.status_code == 201
    data = response.get_json()
    assert 'message' in data


def test_create_user_with_custom_balance(client, monkeypatch):
    monkeypatch.setattr(user_service, 'create_user', lambda **_: None)

    new_user = {
        'username': 'testuser2',
        'firstname': 'Test',
        'lastname': 'User',
        'balance': 500.0,
    }
    response = client.post('/users/', json=new_user)
    assert response.status_code == 201
    data = response.get_json()
    assert 'message' in data


def test_create_user_duplicate_username(client, monkeypatch):
    def mock_create(**kwargs):
        raise user_service.UnsupportedUserOperationError('User already exists')

    monkeypatch.setattr(user_service, 'create_user', mock_create)

    duplicate_user = {
        'username': 'admin',
        'firstname': 'Test',
        'lastname': 'User',
    }
    response = client.post('/users/', json=duplicate_user)
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_update_balance_success(client, monkeypatch):
    monkeypatch.setattr(user_service, 'update_user_balance', lambda **_: None)
    update_data = {'username': 'testuser', 'new_balance': 500.0}
    response = client.put('/users/update-balance', json=update_data)
    assert response.status_code == 200
    data = response.get_json()
    assert 'message' in data


def test_update_balance_user_not_found(client, monkeypatch):
    def mock_update(**_):
        raise user_service.UnsupportedUserOperationError('User not found')

    monkeypatch.setattr(user_service, 'update_user_balance', mock_update)

    update_data = {'username': 'nonexistent_user_xyz', 'new_balance': 100.0}
    response = client.put('/users/update-balance', json=update_data)
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data


def test_delete_user_success(client, monkeypatch):
    # Mock service
    monkeypatch.setattr(user_service, 'delete_user', lambda _: None)
    response = client.delete('/users/testuser')
    assert response.status_code == 200
    data = response.get_json()
    assert 'message' in data


def test_delete_user_not_found(client, monkeypatch):
    def mock_delete(_):
        raise user_service.UnsupportedUserOperationError('User not found')

    monkeypatch.setattr(user_service, 'delete_user', mock_delete)

    response = client.delete('/users/nonexistent_user_xyz')
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data


def test_delete_admin_user(client, monkeypatch):
    def mock_delete(_):
        raise user_service.UnsupportedUserOperationError('Cannot delete admin user')

    monkeypatch.setattr(user_service, 'delete_user', mock_delete)

    response = client.delete('/users/admin')
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data


def test_create_user_missing_required_fields(client):
    incomplete_user = {'username': 'incomplete', 'lastname': 'User'}
    response = client.post('/users/', json=incomplete_user)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_create_user_invalid_field_types(client):
    # Balance should be float, not string
    invalid_user = {
        'username': 'testuser3',
        'firstname': 'Test',
        'lastname': 'User',
        'balance': 'not_a_number',
    }
    response = client.post('/users/', json=invalid_user)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_create_user_username_too_long(client):
    # Username exceeds 30 character limit
    long_username = 'a' * 31
    invalid_user = {
        'username': long_username,
        'firstname': 'Test',
        'lastname': 'User',
    }
    response = client.post('/users/', json=invalid_user)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_create_user_negative_balance(client):
    # Negative balance violates constraint
    invalid_user = {
        'username': 'testuser5',
        'firstname': 'Test',
        'lastname': 'User',
        'balance': -100.0,
    }
    response = client.post('/users/', json=invalid_user)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_update_balance_missing_fields(client):
    # Missing new_balance field
    incomplete_data = {'username': 'someuser'}
    response = client.put('/users/update-balance', json=incomplete_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_update_balance_invalid_types(client):
    # new_balance should be float, not string
    invalid_data = {'username': 'someuser', 'new_balance': 'not_a_number'}
    response = client.put('/users/update-balance', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_update_balance_negative_balance(client):
    # Negative balance violates constraint
    invalid_data = {'username': 'someuser', 'new_balance': -50.0}
    response = client.put('/users/update-balance', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


# =============================================================================
# INTEGRATION TESTS - Full route functionality with DB
# =============================================================================


def test_create_and_retrieve_user_integration(client):
    """Integration test: Create user then retrieve it to verify persistence."""
    # Create user
    new_user = {
        'username': 'integrationuser1',
        'firstname': 'Integration',
        'lastname': 'User',
        'balance': 250.0,
    }
    create_response = client.post('/users/', json=new_user)
    assert create_response.status_code == 201

    # Retrieve the same user
    get_response = client.get('/users/integrationuser1')
    assert get_response.status_code == 200
    data = get_response.get_json()
    assert data['username'] == 'integrationuser1'
    assert data['firstname'] == 'Integration'
    assert data['balance'] == 250.0


def test_update_balance_and_verify_integration(client):
    """Integration test: Update balance then verify the change persisted."""
    # Create user
    new_user = {
        'username': 'integrationuser2',
        'firstname': 'Integration',
        'lastname': 'User',
        'balance': 100.0,
    }
    client.post('/users/', json=new_user)

    # Update balance
    update_data = {'username': 'integrationuser2', 'new_balance': 750.0}
    update_response = client.put('/users/update-balance', json=update_data)
    assert update_response.status_code == 200

    # Verify balance was updated
    get_response = client.get('/users/integrationuser2')
    assert get_response.status_code == 200
    data = get_response.get_json()
    assert data['balance'] == 750.0


def test_delete_user_and_verify_gone_integration(client):
    """Integration test: Delete user then verify it's no longer accessible."""
    # Create user
    new_user = {
        'username': 'integrationuser3',
        'firstname': 'Integration',
        'lastname': 'User',
    }
    client.post('/users/', json=new_user)

    # Delete user
    delete_response = client.delete('/users/integrationuser3')
    assert delete_response.status_code == 200

    # Verify user is gone
    get_response = client.get('/users/integrationuser3')
    assert get_response.status_code == 404


def test_get_user_transactions_empty_list(client, monkeypatch):
    monkeypatch.setattr(transaction_service, 'get_transactions_by_user', lambda _: [])

    response = client.get('/users/testuser/transactions')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_user_transactions_with_data(client, monkeypatch):
    call_count = {'count': 0}

    mock_transaction1 = Transaction(
        username='testuser',
        portfolio_id=1,
        ticker='AAPL',
        transaction_type='BUY',
        quantity=10,
        price=150.0,
        date_time=datetime.datetime(2026, 1, 7, 10, 30, 0),
    )
    mock_transaction1.transaction_id = 1

    mock_transaction2 = Transaction(
        username='testuser',
        portfolio_id=1,
        ticker='GOOGL',
        transaction_type='SELL',
        quantity=5,
        price=2800.0,
        date_time=datetime.datetime(2026, 1, 7, 14, 45, 0),
    )
    mock_transaction2.transaction_id = 2

    def mock_get_transactions(_):
        call_count['count'] += 1
        return [mock_transaction1, mock_transaction2]

    monkeypatch.setattr(transaction_service, 'get_transactions_by_user', mock_get_transactions)

    response = client.get('/users/testuser/transactions')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert call_count['count'] == 1

    # Verify first transaction
    assert data[0]['transaction_id'] == 1
    assert data[0]['username'] == 'testuser'
    assert data[0]['portfolio_id'] == 1
    assert data[0]['ticker'] == 'AAPL'
    assert data[0]['transaction_type'] == 'BUY'
    assert data[0]['quantity'] == 10
    assert data[0]['price'] == 150.0
    assert data[0]['date_time'] == '2026-01-07T10:30:00'

    # Verify second transaction
    assert data[1]['transaction_id'] == 2
    assert data[1]['username'] == 'testuser'
    assert data[1]['ticker'] == 'GOOGL'
    assert data[1]['transaction_type'] == 'SELL'


def test_get_users_exception_handler(client, monkeypatch):
    """Test exception handler in get_users endpoint."""

    def mock_get_all():
        raise Exception('Database connection error')

    monkeypatch.setattr(user_service, 'get_all_users', mock_get_all)

    response = client.get('/users/')
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_get_user_exception_handler(client, monkeypatch):
    """Test exception handler in get_user endpoint."""

    def mock_get_user(_):
        raise Exception('Database query error')

    monkeypatch.setattr(user_service, 'get_user_by_username', mock_get_user)

    response = client.get('/users/testuser')
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_get_user_transactions_exception_handler(client, monkeypatch):
    """Test exception handler in get_user_transactions endpoint."""

    def mock_get_transactions(_):
        raise Exception('Transaction query failed')

    monkeypatch.setattr(transaction_service, 'get_transactions_by_user', mock_get_transactions)

    response = client.get('/users/testuser/transactions')
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data
