import pytest
from app.models import User, Portfolio
from app.service import transaction_service

@pytest.fixture(autouse=True)
def setup_db_with_transactions(db_session):
    # create a test user
    test_user = User(username='testuser', password='testpass', firstname='Test', lastname='User', balance=1000.00)
    db_session.add(test_user)
    db_session.commit()
    # create a test portfolio
    test_portfolio = Portfolio(name='Test Portfolio', description='A portfolio for testing', user=test_user)
    db_session.add(test_portfolio)
    db_session.commit()
    yield

def test_record_transaction_valid(db_session):
    portfolio = db_session.query(Portfolio).filter_by(name='Test Portfolio').one()
    transaction_id = transaction_service.record_transaction(
        portfolio_id=portfolio.id,
        ticker='AAPL',
        quantity=10,
        price=150.0,
        transaction_type='BUY'
    )
    assert transaction_id is not None
    # query transaction by user
    transactions = transaction_service.get_transactions_by_user('testuser')
    assert len(transactions) == 1
    assert transactions[0].transaction_id == transaction_id
    # query transaction by portfolio id
    transactions_by_portfolio = transaction_service.get_transactions_by_portfolio_id(portfolio.id)
    assert len(transactions_by_portfolio) == 1
    assert transactions_by_portfolio[0].transaction_id == transaction_id
    # query transaction by ticker
    transactions_by_ticker = transaction_service.get_transactions_by_ticker('AAPL')
    assert len(transactions_by_ticker) == 1
    assert transactions_by_ticker[0].transaction_id == transaction_id
    
    with pytest.raises(transaction_service.TransactionOperationError) as e:
        transaction_service.record_transaction(
            portfolio_id=portfolio.id,
            ticker='AAPL',
            quantity=-5,
            price=150.0,
            transaction_type='BUY'
        )
    assert "Invalid transaction parameters" in str(e.value)

def test_record_transaction_invalid_portfolio(db_session):
    with pytest.raises(transaction_service.TransactionOperationError) as e:
        transaction_service.record_transaction(
            portfolio_id=9999,  # non-existent portfolio
            ticker='AAPL',
            quantity=10,
            price=150.0,
            transaction_type='BUY'
        )
    assert "Portfolio with id 9999 does not exist" in str(e.value)

def test_record_transaction_invalid_security(db_session):
    portfolio = db_session.query(Portfolio).filter_by(name='Test Portfolio').one()
    with pytest.raises(transaction_service.TransactionOperationError) as e:
        transaction_service.record_transaction(
            portfolio_id=portfolio.id,
            ticker='INVALID',  # non-existent ticker
            quantity=10,
            price=150.0,
            transaction_type='BUY'
        )
    assert "Security with ticker INVALID does not exist" in str(e.value)