import datetime

import app.service.security_service as security_service
import app.service.transaction_service as transaction_service
from app.models import Transaction
from app.service.alpha_vantage_client import SecurityQuote

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
