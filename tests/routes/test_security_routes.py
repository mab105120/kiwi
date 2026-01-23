import datetime

import pytest

import app.service.security_service as security_service
import app.service.transaction_service as transaction_service
from app.models import Portfolio, Transaction, User
from app.service.alpha_vantage_client import SecurityQuote

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


def test_get_security_success(client, monkeypatch):
    mock_quote = SecurityQuote(ticker='AAPL', issuer='Apple Inc.', price=150.00, date='2026-01-08')

    monkeypatch.setattr(security_service, 'get_security_by_ticker', lambda _: mock_quote)

    response = client.get('/securities/AAPL')
    assert response.status_code == 200
    data = response.get_json()
    assert data['ticker'] == 'AAPL'
    assert data['issuer'] == 'Apple Inc.'
    assert data['price'] == 150.00
    assert data['date'] == '2026-01-08'


def test_get_security_not_found(client, monkeypatch):
    monkeypatch.setattr(security_service, 'get_security_by_ticker', lambda _: None)

    response = client.get('/securities/NONEXISTENT')
    assert response.status_code == 404
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_execute_purchase_order_success(client, monkeypatch):
    call_count = {'count': 0}

    def mock_purchase(**kwargs):
        call_count['count'] += 1

    monkeypatch.setattr(security_service, 'execute_purchase_order', mock_purchase)

    purchase_data = {'portfolio_id': 1, 'ticker': 'AAPL', 'quantity': 10}
    response = client.post('/securities/purchase', json=purchase_data)
    assert response.status_code == 201
    data = response.get_json()
    assert 'message' in data
    assert call_count['count'] == 1


def test_execute_purchase_order_portfolio_not_found(client, monkeypatch):
    def mock_purchase(**_):
        raise Exception('Portfolio not found')

    monkeypatch.setattr(security_service, 'execute_purchase_order', mock_purchase)

    purchase_data = {'portfolio_id': 999, 'ticker': 'AAPL', 'quantity': 10}
    response = client.post('/securities/purchase', json=purchase_data)
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_execute_purchase_order_security_not_found(client, monkeypatch):
    def mock_purchase(**_):
        raise Exception('Security not found')

    monkeypatch.setattr(security_service, 'execute_purchase_order', mock_purchase)

    purchase_data = {'portfolio_id': 1, 'ticker': 'INVALID', 'quantity': 10}
    response = client.post('/securities/purchase', json=purchase_data)
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_execute_purchase_order_insufficient_funds(client, monkeypatch):
    def mock_purchase(**_):
        raise security_service.InsufficientFundsError('Insufficient funds')

    monkeypatch.setattr(security_service, 'execute_purchase_order', mock_purchase)

    purchase_data = {'portfolio_id': 1, 'ticker': 'AAPL', 'quantity': 1000}
    response = client.post('/securities/purchase', json=purchase_data)
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_execute_purchase_order_service_error(client, monkeypatch):
    def mock_purchase(**_):
        raise Exception('Database error')

    monkeypatch.setattr(security_service, 'execute_purchase_order', mock_purchase)

    purchase_data = {'portfolio_id': 1, 'ticker': 'AAPL', 'quantity': 10}
    response = client.post('/securities/purchase', json=purchase_data)
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


# =============================================================================
# INPUT VALIDATION TESTS - Pydantic schema validation
# =============================================================================


def test_purchase_missing_portfolio_id(client):
    incomplete_data = {'ticker': 'AAPL', 'quantity': 10}
    response = client.post('/securities/purchase', json=incomplete_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_purchase_missing_ticker(client):
    incomplete_data = {'portfolio_id': 1, 'quantity': 10}
    response = client.post('/securities/purchase', json=incomplete_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_purchase_missing_quantity(client):
    incomplete_data = {'portfolio_id': 1, 'ticker': 'AAPL'}
    response = client.post('/securities/purchase', json=incomplete_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_purchase_zero_portfolio_id(client):
    invalid_data = {'portfolio_id': 0, 'ticker': 'AAPL', 'quantity': 10}
    response = client.post('/securities/purchase', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_purchase_negative_portfolio_id(client):
    invalid_data = {'portfolio_id': -1, 'ticker': 'AAPL', 'quantity': 10}
    response = client.post('/securities/purchase', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_purchase_empty_ticker(client):
    invalid_data = {'portfolio_id': 1, 'ticker': '', 'quantity': 10}
    response = client.post('/securities/purchase', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_purchase_ticker_too_long(client):
    long_ticker = 'A' * 11
    invalid_data = {'portfolio_id': 1, 'ticker': long_ticker, 'quantity': 10}
    response = client.post('/securities/purchase', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_purchase_zero_quantity(client):
    invalid_data = {'portfolio_id': 1, 'ticker': 'AAPL', 'quantity': 0}
    response = client.post('/securities/purchase', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_purchase_negative_quantity(client):
    invalid_data = {'portfolio_id': 1, 'ticker': 'AAPL', 'quantity': -10}
    response = client.post('/securities/purchase', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


def test_purchase_invalid_field_types(client):
    invalid_data = {'portfolio_id': 'invalid', 'ticker': 123, 'quantity': 'ten'}
    response = client.post('/securities/purchase', json=invalid_data)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error_msg' in data


# =============================================================================
# INTEGRATION TESTS - Full route functionality with DB and mocked API
# =============================================================================


def test_get_security_by_ticker_integration(client, mock_alpha_vantage):
    """Integration test: Retrieve specific security by ticker via API."""
    response = client.get('/securities/AAPL')
    assert response.status_code == 200
    data = response.get_json()
    assert data['ticker'] == 'AAPL'
    assert data['issuer'] == 'Apple Inc.'
    assert data['price'] == 150.00
    assert data['date'] == '2026-01-08'


def test_get_security_not_found_integration(client, mock_alpha_vantage):
    """Integration test: Handle non-existent security."""
    response = client.get('/securities/NONEXISTENT')
    assert response.status_code == 404
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
    response = client.post('/securities/purchase', json=purchase_data)
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


def test_get_security_transactions_empty_list(client, monkeypatch):
    monkeypatch.setattr(transaction_service, 'get_transactions_by_ticker', lambda _: [])

    response = client.get('/securities/AAPL/transactions')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_security_transactions_with_data(client, monkeypatch):
    call_count = {'count': 0}

    mock_transaction1 = Transaction(
        username='user1',
        portfolio_id=1,
        ticker='MSFT',
        transaction_type='BUY',
        quantity=15,
        price=300.0,
        date_time=datetime.datetime(2026, 1, 5, 10, 0, 0),
    )
    mock_transaction1.transaction_id = 20

    mock_transaction2 = Transaction(
        username='user2',
        portfolio_id=3,
        ticker='MSFT',
        transaction_type='BUY',
        quantity=25,
        price=305.0,
        date_time=datetime.datetime(2026, 1, 6, 14, 30, 0),
    )
    mock_transaction2.transaction_id = 21

    def mock_get_transactions(_):
        call_count['count'] += 1
        return [mock_transaction1, mock_transaction2]

    monkeypatch.setattr(transaction_service, 'get_transactions_by_ticker', mock_get_transactions)

    response = client.get('/securities/MSFT/transactions')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert call_count['count'] == 1

    # Verify all transactions are for the same ticker
    assert all(t['ticker'] == 'MSFT' for t in data)

    # Verify transactions have different users/portfolios
    assert data[0]['username'] == 'user1'
    assert data[0]['portfolio_id'] == 1
    assert data[1]['username'] == 'user2'
    assert data[1]['portfolio_id'] == 3

    # Verify price and quantity fields are correctly serialized
    assert isinstance(data[0]['price'], float)
    assert isinstance(data[0]['quantity'], int)
    assert data[0]['price'] == 300.0
    assert data[0]['quantity'] == 15


def test_get_security_exception_handler(client, monkeypatch):
    """Test exception handler in get_security endpoint."""

    def mock_get_security(_):
        raise Exception('API connection error')

    monkeypatch.setattr(security_service, 'get_security_by_ticker', mock_get_security)

    response = client.get('/securities/AAPL')
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data


def test_get_security_transactions_exception_handler(client, monkeypatch):
    """Test exception handler in get_security_transactions endpoint."""

    def mock_get_transactions(_):
        raise Exception('Transaction query failed')

    monkeypatch.setattr(transaction_service, 'get_transactions_by_ticker', mock_get_transactions)

    response = client.get('/securities/AAPL/transactions')
    assert response.status_code == 500
    data = response.get_json()
    assert 'error_msg' in data
    assert 'request_id' in data
