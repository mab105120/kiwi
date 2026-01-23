import datetime

import pytest

import app.service.portfolio_service as portfolio_service
import app.service.transaction_service as transaction_service
import app.service.user_service as user_service
from app.models import Portfolio, Transaction, User

# =============================================================================
# FIXTURES - Module-specific test data
# =============================================================================


@pytest.fixture(scope='function')
def test_user_with_portfolio(db_session):
    user = User(
        username='securitytestuser',
        firstname='Security',
        lastname='Tester',
        balance=10000.00,
    )
    db_session.add(user)
    db_session.flush()

    portfolio = Portfolio(
        name='Test Security Portfolio',
        description='Portfolio for testing security purchases',
        user=user,
    )
    db_session.add(portfolio)
    db_session.flush()

    return {'user': user, 'portfolio': portfolio, 'initial_balance': 10000.00}


# =============================================================================
# UNIT TESTS - Mocked service calls
# =============================================================================


def test_get_all_portfolios_empty_list(client, monkeypatch):
    monkeypatch.setattr(portfolio_service, 'get_all_portfolios', lambda: [])

    response = client.get('/portfolios/')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_all_portfolios_with_data(client, monkeypatch):
    mock_portfolio1 = Portfolio(id=1, name='Portfolio 1', description='Desc 1')
    mock_portfolio1.owner = 'user1'
    mock_portfolio1.investments = []
    mock_portfolio2 = Portfolio(id=2, name='Portfolio 2', description='Desc 2')
    mock_portfolio2.owner = 'user2'
    mock_portfolio2.investments = []

    monkeypatch.setattr(portfolio_service, 'get_all_portfolios', lambda: [mock_portfolio1, mock_portfolio2])

    response = client.get('/portfolios/')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]['name'] == 'Portfolio 1'
    assert data[1]['name'] == 'Portfolio 2'


def test_get_portfolio_success(client, monkeypatch):
    mock_portfolio = Portfolio(id=1, name='Test Portfolio', description='Test Desc')
    mock_portfolio.owner = 'testuser'
    mock_portfolio.investments = []

    monkeypatch.setattr(portfolio_service, 'get_portfolio_by_id', lambda _: mock_portfolio)

    response = client.get('/portfolios/1')
    assert response.status_code == 200
    data = response.get_json()
    assert data['id'] == 1
    assert data['name'] == 'Test Portfolio'
    assert data['description'] == 'Test Desc'
    assert data['owner'] == 'testuser'
    assert 'investments_count' in data


def test_get_portfolio_not_found(client, monkeypatch):
    monkeypatch.setattr(portfolio_service, 'get_portfolio_by_id', lambda _: None)

    response = client.get('/portfolios/999')
    assert response.status_code == 404
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_get_portfolios_by_user_success(client, monkeypatch):
    call_count = {'count': 0}

    mock_user = User(username='testuser', firstname='Test', lastname='User', balance=1000.0)
    mock_portfolio = Portfolio(id=1, name='User Portfolio', description='Desc')
    mock_portfolio.owner = 'testuser'
    mock_portfolio.investments = []

    def mock_get_portfolios(_):
        call_count['count'] += 1
        return [mock_portfolio]

    monkeypatch.setattr(user_service, 'get_user_by_username', lambda _: mock_user)
    monkeypatch.setattr(portfolio_service, 'get_portfolios_by_user', mock_get_portfolios)

    response = client.get('/portfolios/user/testuser')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert call_count['count'] == 1


def test_get_portfolios_by_user_not_found(client, monkeypatch):
    call_count = {'count': 0}

    def mock_get_portfolios(_):
        call_count['count'] += 1
        return []

    monkeypatch.setattr(user_service, 'get_user_by_username', lambda _: None)
    monkeypatch.setattr(portfolio_service, 'get_portfolios_by_user', mock_get_portfolios)

    response = client.get('/portfolios/user/nonexistent')
    assert response.status_code == 404
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data
    assert call_count['count'] == 0


def test_get_portfolios_by_user_empty_list(client, monkeypatch):
    mock_user = User(username='testuser', firstname='Test', lastname='User', balance=1000.0)

    monkeypatch.setattr(user_service, 'get_user_by_username', lambda _: mock_user)
    monkeypatch.setattr(portfolio_service, 'get_portfolios_by_user', lambda _: [])

    response = client.get('/portfolios/user/testuser')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_create_portfolio_success(client, monkeypatch):
    call_count = {'count': 0}

    mock_user = User(username='testuser', firstname='Test', lastname='User', balance=1000.0)

    def mock_create(**_):
        call_count['count'] += 1
        return 123

    monkeypatch.setattr(user_service, 'get_user_by_username', lambda _: mock_user)
    monkeypatch.setattr(portfolio_service, 'create_portfolio', mock_create)

    new_portfolio = {
        'name': 'New Portfolio',
        'description': 'Portfolio description',
        'username': 'testuser',
    }
    response = client.post('/portfolios/', json=new_portfolio)
    assert response.status_code == 201
    data = response.get_json()
    assert 'message' in data
    assert 'portfolio_id' in data
    assert data['portfolio_id'] == 123
    assert call_count['count'] == 1


def test_create_portfolio_user_not_found(client, monkeypatch):
    call_count = {'count': 0}

    def mock_create(**_):
        call_count['count'] += 1
        return 123

    monkeypatch.setattr(user_service, 'get_user_by_username', lambda _: None)
    monkeypatch.setattr(portfolio_service, 'create_portfolio', mock_create)

    new_portfolio = {
        'name': 'New Portfolio',
        'description': 'Portfolio description',
        'username': 'nonexistent',
    }
    response = client.post('/portfolios/', json=new_portfolio)
    assert response.status_code == 404
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data
    assert call_count['count'] == 0


def test_create_portfolio_service_error(client, monkeypatch):
    mock_user = User(username='testuser', firstname='Test', lastname='User', balance=1000.0)

    def mock_create(**_):
        raise Exception('Database error')

    monkeypatch.setattr(user_service, 'get_user_by_username', lambda _: mock_user)
    monkeypatch.setattr(portfolio_service, 'create_portfolio', mock_create)

    new_portfolio = {
        'name': 'New Portfolio',
        'description': 'Portfolio description',
        'username': 'testuser',
    }
    response = client.post('/portfolios/', json=new_portfolio)
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_delete_portfolio_success(client, monkeypatch):
    call_count = {'count': 0}

    def mock_delete(_):
        call_count['count'] += 1

    monkeypatch.setattr(portfolio_service, 'delete_portfolio', mock_delete)

    response = client.delete('/portfolios/1')
    assert response.status_code == 200
    data = response.get_json()
    assert 'message' in data
    assert call_count['count'] == 1


def test_delete_portfolio_not_found(client, monkeypatch):
    def mock_delete(_):
        raise Exception('Portfolio not found')

    monkeypatch.setattr(portfolio_service, 'delete_portfolio', mock_delete)

    response = client.delete('/portfolios/999')
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_liquidate_investment_success(client, monkeypatch):
    call_count = {'count': 0}

    def mock_liquidate(**_):
        call_count['count'] += 1

    monkeypatch.setattr(portfolio_service, 'liquidate_investment', mock_liquidate)

    liquidate_data = {'ticker': 'AAPL', 'quantity': 10}
    response = client.post('/portfolios/1/liquidate/', json=liquidate_data)
    assert response.status_code == 200
    data = response.get_json()
    assert 'message' in data
    assert call_count['count'] == 1


def test_liquidate_investment_portfolio_not_found(client, monkeypatch):
    def mock_liquidate(**_):
        raise Exception('Portfolio not found')

    monkeypatch.setattr(portfolio_service, 'liquidate_investment', mock_liquidate)

    liquidate_data = {'ticker': 'AAPL', 'quantity': 10}
    response = client.post('/portfolios/999/liquidate/', json=liquidate_data)
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_liquidate_investment_ticker_not_found(client, monkeypatch):
    def mock_liquidate(**_):
        raise Exception('Investment with ticker XXXX not found')

    monkeypatch.setattr(portfolio_service, 'liquidate_investment', mock_liquidate)

    liquidate_data = {'ticker': 'XXXX', 'quantity': 10}
    response = client.post('/portfolios/1/liquidate/', json=liquidate_data)
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_liquidate_investment_insufficient_quantity(client, monkeypatch):
    def mock_liquidate(**_):
        raise Exception('Insufficient quantity available')

    monkeypatch.setattr(portfolio_service, 'liquidate_investment', mock_liquidate)

    liquidate_data = {'ticker': 'AAPL', 'quantity': 1000}
    response = client.post('/portfolios/1/liquidate/', json=liquidate_data)
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_execute_purchase_order_success(client, monkeypatch):
    call_count = {'count': 0}

    def mock_purchase(**kwargs):
        call_count['count'] += 1

    monkeypatch.setattr(portfolio_service, 'execute_purchase_order', mock_purchase)

    purchase_data = {'portfolio_id': 1, 'ticker': 'AAPL', 'quantity': 10}
    response = client.post('/portfolios/purchase', json=purchase_data)
    assert response.status_code == 201
    data = response.get_json()
    assert 'message' in data
    assert call_count['count'] == 1


def test_execute_purchase_order_portfolio_not_found(client, monkeypatch):
    def mock_purchase(**_):
        raise Exception('Portfolio not found')

    monkeypatch.setattr(portfolio_service, 'execute_purchase_order', mock_purchase)

    purchase_data = {'portfolio_id': 999, 'ticker': 'AAPL', 'quantity': 10}
    response = client.post('/portfolios/purchase', json=purchase_data)
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_execute_purchase_order_security_not_found(client, monkeypatch):
    def mock_purchase(**_):
        raise Exception('Security not found')

    monkeypatch.setattr(portfolio_service, 'execute_purchase_order', mock_purchase)

    purchase_data = {'portfolio_id': 1, 'ticker': 'INVALID', 'quantity': 10}
    response = client.post('/portfolios/purchase', json=purchase_data)
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_execute_purchase_order_insufficient_funds(client, monkeypatch):
    def mock_purchase(**_):
        raise portfolio_service.InsufficientFundsError('Insufficient funds')

    monkeypatch.setattr(portfolio_service, 'execute_purchase_order', mock_purchase)

    purchase_data = {'portfolio_id': 1, 'ticker': 'AAPL', 'quantity': 1000}
    response = client.post('/portfolios/purchase', json=purchase_data)
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_execute_purchase_order_service_error(client, monkeypatch):
    def mock_purchase(**_):
        raise Exception('Database error')

    monkeypatch.setattr(portfolio_service, 'execute_purchase_order', mock_purchase)

    purchase_data = {'portfolio_id': 1, 'ticker': 'AAPL', 'quantity': 10}
    response = client.post('/securities/purchase', json=purchase_data)
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


# =============================================================================
# INPUT VALIDATION TESTS - Pydantic schema validation
# =============================================================================


def test_create_portfolio_missing_name(client):
    incomplete_data = {'description': 'Test description', 'username': 'testuser'}
    response = client.post('/portfolios/', json=incomplete_data)

    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data
    assert response.status_code == 400


def test_create_portfolio_missing_description(client):
    incomplete_data = {'name': 'Test Portfolio', 'username': 'testuser'}
    response = client.post('/portfolios/', json=incomplete_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_create_portfolio_missing_username(client):
    incomplete_data = {'name': 'Test Portfolio', 'description': 'Test description'}
    response = client.post('/portfolios/', json=incomplete_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_create_portfolio_empty_name(client):
    invalid_data = {'name': '', 'description': 'Test description', 'username': 'testuser'}
    response = client.post('/portfolios/', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_create_portfolio_name_too_long(client):
    long_name = 'a' * 31
    invalid_data = {'name': long_name, 'description': 'Test description', 'username': 'testuser'}
    response = client.post('/portfolios/', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_create_portfolio_empty_description(client):
    invalid_data = {'name': 'Test Portfolio', 'description': '', 'username': 'testuser'}
    response = client.post('/portfolios/', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_create_portfolio_description_too_long(client):
    long_description = 'a' * 501
    invalid_data = {'name': 'Test Portfolio', 'description': long_description, 'username': 'testuser'}
    response = client.post('/portfolios/', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_create_portfolio_username_too_long(client):
    long_username = 'a' * 31
    invalid_data = {'name': 'Test Portfolio', 'description': 'Test description', 'username': long_username}
    response = client.post('/portfolios/', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_create_portfolio_invalid_field_types(client):
    invalid_data = {'name': 123, 'description': True, 'username': ['invalid']}
    response = client.post('/portfolios/', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_liquidate_investment_missing_ticker(client):
    incomplete_data = {'quantity': 10}
    response = client.post('/portfolios/1/liquidate/', json=incomplete_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_liquidate_investment_missing_quantity(client):
    incomplete_data = {'ticker': 'AAPL'}
    response = client.post('/portfolios/1/liquidate/', json=incomplete_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_liquidate_investment_empty_ticker(client):
    invalid_data = {'ticker': '', 'quantity': 10}
    response = client.post('/portfolios/1/liquidate/', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_liquidate_investment_ticker_too_long(client):
    long_ticker = 'A' * 11
    invalid_data = {'ticker': long_ticker, 'quantity': 10}
    response = client.post('/portfolios/1/liquidate/', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_liquidate_investment_zero_quantity(client):
    invalid_data = {'ticker': 'AAPL', 'quantity': 0}
    response = client.post('/portfolios/1/liquidate/', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_liquidate_investment_negative_quantity(client):
    invalid_data = {'ticker': 'AAPL', 'quantity': -10}
    response = client.post('/portfolios/1/liquidate/', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_liquidate_investment_invalid_types(client):
    invalid_data = {'ticker': 'AAPL', 'quantity': 'ten'}
    response = client.post('/portfolios/1/liquidate/', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_purchase_missing_portfolio_id(client):
    incomplete_data = {'ticker': 'AAPL', 'quantity': 10}
    response = client.post('/portfolios/purchase', json=incomplete_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_purchase_missing_ticker(client):
    incomplete_data = {'portfolio_id': 1, 'quantity': 10}
    response = client.post('/portfolios/purchase', json=incomplete_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_purchase_missing_quantity(client):
    incomplete_data = {'portfolio_id': 1, 'ticker': 'AAPL'}
    response = client.post('/portfolios/purchase', json=incomplete_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_purchase_zero_portfolio_id(client):
    invalid_data = {'portfolio_id': 0, 'ticker': 'AAPL', 'quantity': 10}
    response = client.post('/portfolios/purchase', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_purchase_negative_portfolio_id(client):
    invalid_data = {'portfolio_id': -1, 'ticker': 'AAPL', 'quantity': 10}
    response = client.post('/portfolios/purchase', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_purchase_empty_ticker(client):
    invalid_data = {'portfolio_id': 1, 'ticker': '', 'quantity': 10}
    response = client.post('/portfolios/purchase', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_purchase_ticker_too_long(client):
    long_ticker = 'A' * 11
    invalid_data = {'portfolio_id': 1, 'ticker': long_ticker, 'quantity': 10}
    response = client.post('/portfolios/purchase', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_purchase_zero_quantity(client):
    invalid_data = {'portfolio_id': 1, 'ticker': 'AAPL', 'quantity': 0}
    response = client.post('/portfolios/purchase', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_purchase_negative_quantity(client):
    invalid_data = {'portfolio_id': 1, 'ticker': 'AAPL', 'quantity': -10}
    response = client.post('/portfolios/purchase', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_purchase_invalid_field_types(client):
    invalid_data = {'portfolio_id': 'invalid', 'ticker': 123, 'quantity': 'ten'}
    response = client.post('/portfolios/purchase', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


# =============================================================================
# INTEGRATION TESTS - Full route functionality with DB
# =============================================================================


def test_create_and_retrieve_portfolio_integration(client):
    """Integration test: Create portfolio then retrieve it to verify persistence."""
    new_portfolio = {
        'name': 'Integration Portfolio 1',
        'description': 'Testing end-to-end creation and retrieval',
        'username': 'admin',
    }
    create_response = client.post('/portfolios/', json=new_portfolio)
    assert create_response.status_code == 201
    portfolio_id = create_response.get_json()['portfolio_id']

    get_response = client.get(f'/portfolios/{portfolio_id}')
    assert get_response.status_code == 200
    data = get_response.get_json()
    assert data['name'] == 'Integration Portfolio 1'
    assert data['description'] == 'Testing end-to-end creation and retrieval'
    assert data['owner'] == 'admin'


def test_create_portfolio_and_get_by_user_integration(client):
    """Integration test: Create portfolio then verify it appears in user's list."""
    new_portfolio = {
        'name': 'Integration Portfolio 2',
        'description': 'Testing user portfolio list',
        'username': 'admin',
    }
    create_response = client.post('/portfolios/', json=new_portfolio)
    assert create_response.status_code == 201

    get_response = client.get('/portfolios/user/admin')
    assert get_response.status_code == 200
    data = get_response.get_json()
    assert isinstance(data, list)
    portfolio_names = [p['name'] for p in data]
    assert 'Integration Portfolio 2' in portfolio_names


def test_delete_portfolio_and_verify_gone_integration(client):
    """Integration test: Delete portfolio then verify it's no longer accessible."""
    new_portfolio = {
        'name': 'Integration Portfolio 3',
        'description': 'Testing deletion',
        'username': 'admin',
    }
    create_response = client.post('/portfolios/', json=new_portfolio)
    assert create_response.status_code == 201
    portfolio_id = create_response.get_json()['portfolio_id']

    delete_response = client.delete(f'/portfolios/{portfolio_id}')
    assert delete_response.status_code == 200

    get_response = client.get(f'/portfolios/{portfolio_id}')
    assert get_response.status_code == 404


def test_get_portfolio_transactions_empty_list(client, monkeypatch):
    monkeypatch.setattr(transaction_service, 'get_transactions_by_portfolio_id', lambda _: [])

    response = client.get('/portfolios/1/transactions')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_portfolio_transactions_with_data(client, monkeypatch):
    call_count = {'count': 0}

    mock_transaction1 = Transaction(
        username='user1',
        portfolio_id=5,
        ticker='AAPL',
        transaction_type='BUY',
        quantity=10,
        price=150.0,
        date_time=datetime.datetime(2026, 1, 5, 9, 0, 0),
    )
    mock_transaction1.transaction_id = 10

    mock_transaction2 = Transaction(
        username='user1',
        portfolio_id=5,
        ticker='MSFT',
        transaction_type='BUY',
        quantity=20,
        price=300.0,
        date_time=datetime.datetime(2026, 1, 6, 11, 15, 0),
    )
    mock_transaction2.transaction_id = 11

    mock_transaction3 = Transaction(
        username='user1',
        portfolio_id=5,
        ticker='AAPL',
        transaction_type='SELL',
        quantity=5,
        price=155.0,
        date_time=datetime.datetime(2026, 1, 7, 15, 30, 0),
    )
    mock_transaction3.transaction_id = 12

    def mock_get_transactions(_):
        call_count['count'] += 1
        return [mock_transaction1, mock_transaction2, mock_transaction3]

    monkeypatch.setattr(transaction_service, 'get_transactions_by_portfolio_id', mock_get_transactions)

    response = client.get('/portfolios/5/transactions')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 3
    assert call_count['count'] == 1

    # Verify all transactions belong to portfolio_id 5
    assert all(t['portfolio_id'] == 5 for t in data)

    # Verify mix of transaction types
    transaction_types = [t['transaction_type'] for t in data]
    assert 'BUY' in transaction_types
    assert 'SELL' in transaction_types

    # Verify first transaction details
    assert data[0]['transaction_id'] == 10
    assert data[0]['ticker'] == 'AAPL'
    assert data[0]['transaction_type'] == 'BUY'


def test_get_all_portfolios_exception_handler(client, monkeypatch):
    """Test exception handler in get_all_portfolios endpoint."""

    def mock_get_all():
        raise Exception('Database connection error')

    monkeypatch.setattr(portfolio_service, 'get_all_portfolios', mock_get_all)

    response = client.get('/portfolios/')
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_get_portfolio_exception_handler(client, monkeypatch):
    """Test exception handler in get_portfolio endpoint."""

    def mock_get_portfolio(_):
        raise Exception('Database query error')

    monkeypatch.setattr(portfolio_service, 'get_portfolio_by_id', mock_get_portfolio)

    response = client.get('/portfolios/1')
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_get_portfolios_by_user_exception_handler(client, monkeypatch):
    """Test exception handler in get_portfolios_by_user endpoint."""
    mock_user = User(username='testuser', firstname='Test', lastname='User', balance=1000.0)

    def mock_get_portfolios(_):
        raise Exception('Query failed')

    monkeypatch.setattr(user_service, 'get_user_by_username', lambda _: mock_user)
    monkeypatch.setattr(portfolio_service, 'get_portfolios_by_user', mock_get_portfolios)

    response = client.get('/portfolios/user/testuser')
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_get_portfolio_transactions_exception_handler(client, monkeypatch):
    """Test exception handler in get_portfolio_transactions endpoint."""

    def mock_get_transactions(_):
        raise Exception('Transaction query failed')

    monkeypatch.setattr(transaction_service, 'get_transactions_by_portfolio_id', mock_get_transactions)

    response = client.get('/portfolios/1/transactions')
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_execute_purchase_order_integration(client, test_user_with_portfolio, db_session, mock_alpha_vantage):
    """Integration test: Execute full purchase workflow and verify balance update."""
    fixture_data = test_user_with_portfolio
    user = fixture_data['user']
    portfolio = fixture_data['portfolio']
    initial_balance = fixture_data['initial_balance']

    purchase_data = {'portfolio_id': portfolio.id, 'ticker': 'AAPL', 'quantity': 10}
    response = client.post('/portfolios/purchase', json=purchase_data)
    assert response.status_code == 201
    data = response.get_json()
    assert 'message' in data

    expected_cost = 150.00 * 10
    expected_balance = initial_balance - expected_cost

    db_session.expire_all()
    user_from_db = db_session.query(User).filter_by(username=user.username).first()
    assert user_from_db is not None
    assert user_from_db.balance == expected_balance
    assert user_from_db.balance == 8500.00

    portfolio_from_db = db_session.query(Portfolio).filter_by(id=portfolio.id).first()
    assert portfolio_from_db is not None
    assert len(portfolio_from_db.investments) == 1
    investment = portfolio_from_db.investments[0]
    assert investment.ticker == 'AAPL'
    assert investment.quantity == 10
