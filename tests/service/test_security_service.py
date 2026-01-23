import pytest

from app import db
from app.models import Portfolio, User
from app.service import transaction_service
from app.service.portfolio_service import create_portfolio
from app.service.security_service import (
    SecurityException,
    get_security_by_ticker,
)
from app.service.user_service import create_user


@pytest.fixture(autouse=True)
def setup(db_session):
    create_user(
        username='user',
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


def test_get_security_by_ticker_generic_exception(db_session, monkeypatch):
    """Test handling of generic exceptions from API"""
    from app.service import alpha_vantage_client

    def mock_unexpected_error(_):
        raise RuntimeError('Unexpected error occurred')

    monkeypatch.setattr(alpha_vantage_client, 'get_quote', mock_unexpected_error)

    with pytest.raises(SecurityException) as e:
        get_security_by_ticker('AAPL')
    assert 'Failed to retrieve security due to error: Unexpected error occurred' in str(e.value)
