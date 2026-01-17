import pytest

from app.models import Portfolio, User
from app.service import transaction_service
from app.service.portfolio_service import create_portfolio
from app.service.security_service import (
    InsufficientFundsError,
    SecurityException,
    execute_purchase_order,
    get_security_by_ticker,
)
from app.service.user_service import create_user


@pytest.fixture(autouse=True)
def setup(db_session):
    create_user(
        username='user',
        password='secret',
        firstname='Firstname',
        lastname='Lastname',
        balance=1000.00,
    )
    user = db_session.query(User).filter_by(username='user').one()
    assert user is not None
    create_portfolio('Test Portfolio', 'Test Portfolio Description', user)
    portfolio = db_session.query(Portfolio).filter_by(name='Test Portfolio').one()
    assert portfolio is not None
    return {'user': user, 'portfolio': portfolio}


def test_get_security_by_ticker(db_session, mock_alpha_vantage):
    """Test fetching security from API"""
    security_quote = get_security_by_ticker('AAPL')
    assert security_quote is not None
    assert security_quote.ticker == 'AAPL'
    assert security_quote.issuer == 'Apple Inc.'
    assert security_quote.price == 150.00
    assert security_quote.date == '2026-01-08'


def test_get_security_by_ticker_not_found(db_session, mock_alpha_vantage):
    """Test handling of non-existent ticker"""
    security_quote = get_security_by_ticker('NONEXISTENT')
    assert security_quote is None


def test_get_security_by_ticker_api_error(db_session, monkeypatch):
    """Test handling of API errors"""
    from app.service import alpha_vantage_client
    from app.service.alpha_vantage_client import APIConnectionError

    def mock_api_failure(_):
        raise APIConnectionError('API connection failed')

    monkeypatch.setattr(alpha_vantage_client, 'get_quote', mock_api_failure)

    with pytest.raises(SecurityException) as e:
        get_security_by_ticker('AAPL')
    assert 'Failed to retrieve security' in str(e.value)


def test_execute_purchase_order_success(setup, db_session, mock_alpha_vantage):
    """Test successful purchase order execution"""
    portfolio = setup['portfolio']
    user = setup['user']
    initial_balance = user.balance

    execute_purchase_order(portfolio.id, 'AAPL', 5)

    db_session.expire_all()
    user_after = db_session.query(User).filter_by(username='user').one()
    expected_balance = initial_balance - (150.00 * 5)
    assert user_after.balance == expected_balance

    portfolio_after = db_session.query(Portfolio).filter_by(id=portfolio.id).one()
    assert len(portfolio_after.investments) == 1
    assert portfolio_after.investments[0].ticker == 'AAPL'
    assert portfolio_after.investments[0].quantity == 5

    transactions = transaction_service.get_transactions_by_portfolio_id(portfolio.id)
    assert len(transactions) == 1
    assert transactions[0].ticker == 'AAPL'
    assert transactions[0].quantity == 5
    assert transactions[0].price == 150.00
    assert transactions[0].transaction_type == 'BUY'


def test_execute_purchase_order_multiple_same_ticker(setup, db_session, mock_alpha_vantage):
    """Test purchasing same ticker multiple times adds to existing investment"""
    portfolio = setup['portfolio']

    # First purchase: 5 shares at $150 = $750, leaving $250
    execute_purchase_order(portfolio.id, 'AAPL', 5)
    # Second purchase: 1 share at $150 = $150, leaving $100
    execute_purchase_order(portfolio.id, 'AAPL', 1)

    db_session.expire_all()
    portfolio_after = db_session.query(Portfolio).filter_by(id=portfolio.id).one()
    assert len(portfolio_after.investments) == 1
    assert portfolio_after.investments[0].quantity == 6


def test_execute_purchase_order_insufficient_funds(setup, db_session, mock_alpha_vantage):
    """Test purchase order fails with insufficient funds"""
    portfolio = setup['portfolio']

    with pytest.raises(Exception) as e:
        execute_purchase_order(portfolio.id, 'AAPL', 1000)
    assert 'Insufficient funds' in str(e.value)


def test_execute_purchase_order_invalid_portfolio(db_session, mock_alpha_vantage):
    """Test purchase order fails with non-existent portfolio"""
    with pytest.raises(SecurityException) as e:
        execute_purchase_order(9999, 'AAPL', 5)
    assert 'Portfolio with id 9999 does not exist' in str(e.value)


def test_execute_purchase_order_invalid_ticker(setup, db_session, mock_alpha_vantage):
    """Test purchase order fails with non-existent ticker"""
    portfolio = setup['portfolio']

    with pytest.raises(SecurityException) as e:
        execute_purchase_order(portfolio.id, 'NONEXISTENT', 5)
    assert 'does not exist or market data unavailable' in str(e.value)


def test_execute_purchase_order_invalid_parameters(setup, db_session, mock_alpha_vantage):
    """Test purchase order validation"""
    portfolio = setup['portfolio']

    # None portfolio_id
    with pytest.raises(SecurityException) as e:
        execute_purchase_order(None, 'AAPL', 5)  # type: ignore
    assert 'Invalid purchase order parameters' in str(e.value)

    # Empty ticker
    with pytest.raises(SecurityException) as e:
        execute_purchase_order(portfolio.id, '', 5)
    assert 'Invalid purchase order parameters' in str(e.value)

    # Zero quantity
    with pytest.raises(SecurityException) as e:
        execute_purchase_order(portfolio.id, 'AAPL', 0)
    assert 'Invalid purchase order parameters' in str(e.value)

    # Negative quantity
    with pytest.raises(SecurityException) as e:
        execute_purchase_order(portfolio.id, 'AAPL', -5)
    assert 'Invalid purchase order parameters' in str(e.value)
