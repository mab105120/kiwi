import pytest
from app.models import User, Portfolio
from app.service.portfolio_service import create_portfolio
from app.service.security_service import InsufficientFundsError, execute_purchase_order, get_all_securities, SecurityException
from app.service.user_service import create_user
from app.service import transaction_service

@pytest.fixture(autouse=True)
def setup(db_session):
    create_user(username="user", password="secret", firstname="Firstname", lastname="Lastname", balance=1000.00)
    user = db_session.query(User).filter_by(username="user").one()
    assert user is not None
    create_portfolio("Test Portfolio", "Test Portfolio Description", user)
    portfolio = db_session.query(Portfolio).filter_by(name="Test Portfolio").one()
    assert portfolio is not None
    return {
        "user": user,
        "portfolio": portfolio
    }

def test_get_all_securities(db_session):
    securities = get_all_securities()
    assert securities is not None
    assert len(securities) == 3
    tickers = [sec.ticker for sec in securities]
    assert "AAPL" in tickers
    assert "GOOGL" in tickers
    assert "MSFT" in tickers

def test_exception_from_get_all_securities(db_session, monkeypatch):
    def mock_get_session_failure():
        raise Exception("Database connection error")
    monkeypatch.setattr('app.database.get_session', mock_get_session_failure)
    with pytest.raises(SecurityException) as e:
        get_all_securities()
    assert "Failed to retrieve securities due to error: Database connection error" in str(e.value)

def test_execute_purchase_order(setup, db_session):
    portfolio = setup["portfolio"]
    transactions = transaction_service.get_transactions_by_portfolio_id(portfolio.id)
    assert len(transactions) == 0
    user = db_session.query(User).filter_by(username="user").one()
    assert user.balance == 1000.00
    execute_purchase_order(portfolio.id, "AAPL", 2)
    user = db_session.query(User).filter_by(username="user").one()
    assert user.balance == 700.00
    user_portfolio = user.portfolios[0]
    assert user_portfolio.investments is not None
    investments = user_portfolio.investments
    assert len(investments) == 1
    investment = investments[0]
    assert investment.security.ticker == "AAPL"
    assert investment.quantity == 2
    transactions = transaction_service.get_transactions_by_portfolio_id(portfolio.id)
    assert len(transactions) == 1
    assert transactions[0].ticker == "AAPL"
    assert transactions[0].quantity == 2
    assert transactions[0].price == 150.00
    assert transactions[0].transaction_type == "BUY"

def test_execute_purchase_order_insufficient_funds(setup, db_session):
    portfolio = setup["portfolio"]
    with pytest.raises(InsufficientFundsError) as e:
        execute_purchase_order(portfolio.id, "GOOGL", 1)
    assert str(e.value) == "Insufficient funds to complete the purchase."

def test_execute_order_for_nonexistent_portfolio(db_session):
    with pytest.raises(SecurityException) as e:
        execute_purchase_order(999, "AAPL", 1)
    assert "Portfolio with id 999 does not exist." in str(e.value)

def test_execute_order_for_nonexistent_security(setup, db_session):
    portfolio = setup["portfolio"]
    with pytest.raises(SecurityException) as e:
        execute_purchase_order(portfolio.id, "INVALID", 1)
    assert "Security with ticker INVALID does not exist." in str(e.value)