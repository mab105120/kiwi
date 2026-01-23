import datetime

import pytest

from app.models import Portfolio, Transaction, User
from app.service import transaction_service


@pytest.fixture(autouse=True)
def setup(db_session):
    # create a test user
    test_user = User(
        username='testuser',
        firstname='Test',
        lastname='User',
        balance=1000.00,
    )
    db_session.add(test_user)
    db_session.commit()
    # create a test portfolio
    test_portfolio = Portfolio(name='Test Portfolio', description='A portfolio for testing', user=test_user)
    db_session.add(test_portfolio)
    db_session.commit()
    transactions = [
        Transaction(
            portfolio_id=test_portfolio.id,
            username=test_user.username,
            ticker='AAPL',
            quantity=10,
            price=150.00,
            transaction_type='BUY',
            date_time=datetime.datetime.now(),
        ),
        Transaction(
            portfolio_id=test_portfolio.id,
            username=test_user.username,
            ticker='GOOGL',
            quantity=10,
            price=250.00,
            transaction_type='BUY',
            date_time=datetime.datetime.now(),
        ),
    ]
    db_session.add_all(transactions)
    db_session.commit()
    yield {'user': test_user, 'portfolio': test_portfolio}


def test_get_transactions_by_user(setup, db_session):
    user = setup['user']
    transactions = transaction_service.get_transactions_by_user(user.username)
    assert len(transactions) == 2
    assert all(tx.username == user.username for tx in transactions)


def test_get_transactions_by_portfolio(setup, db_session):
    portfolio = setup['portfolio']
    transactions = transaction_service.get_transactions_by_portfolio_id(portfolio.id)
    assert len(transactions) == 2
    assert all(tx.portfolio_id == portfolio.id for tx in transactions)


def test_get_transactions_by_ticker(setup, db_session):
    transactions = transaction_service.get_transactions_by_ticker('AAPL')
    assert len(transactions) == 1
    assert transactions[0].ticker == 'AAPL'


def test_get_transactions_by_user_exception(db_session, monkeypatch):
    def mock_query(*args, **kwargs):
        raise Exception('Database error')

    monkeypatch.setattr(db_session, 'query', mock_query)

    with pytest.raises(Exception) as exc_info:
        transaction_service.get_transactions_by_user('testuser')
    assert 'Database error' in str(exc_info.value)


def test_get_transactions_by_portfolio_id_exception(db_session, monkeypatch):
    def mock_query(*args, **kwargs):
        raise Exception('Database error')

    monkeypatch.setattr(db_session, 'query', mock_query)

    with pytest.raises(Exception) as exc_info:
        transaction_service.get_transactions_by_portfolio_id(1)
    assert 'Database error' in str(exc_info.value)


def test_get_transactions_by_ticker_exception(db_session, monkeypatch):
    def mock_query(*args, **kwargs):
        raise Exception('Database error')

    monkeypatch.setattr(db_session, 'query', mock_query)

    with pytest.raises(Exception) as exc_info:
        transaction_service.get_transactions_by_ticker('AAPL')
    assert 'Database error' in str(exc_info.value)
