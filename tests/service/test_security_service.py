from rich.table import Table

from app.domain import User, Portfolio
from app.service.portfolio_service import _create_portfolio
from app.service.security_service import InsufficientFundsError, get_all_securities, place_purchase_order, SecurityException, _execute_purchase_order, build_securities_table
from app.service.user_service import _create_user
from app.session_state import set_logged_in_user, reset_logged_in_user

def test_get_all_securities(db_session):
    securities = get_all_securities()
    assert securities is not None
    assert len(securities) == 3
    tickers = [sec.ticker for sec in securities]
    assert "AAPL" in tickers
    assert "GOOGL" in tickers
    assert "MSFT" in tickers

def test_execute_purchase_order(db_session):
    _create_user(username="user", password="secret", firstname="Firstname", lastname="Lastname", balance=1000.00)
    user = db_session.query(User).filter_by(username="user").one()
    assert user is not None
    _create_portfolio("Test Portfolio", "Test Portfolio Description", user)
    portfolio = db_session.query(Portfolio).filter_by(name="Test Portfolio").one()
    assert portfolio is not None
    try:
        set_logged_in_user(user)
        order_confirmation = _execute_purchase_order(portfolio.id, "AAPL", 2)
        assert "Purchased 2 shares of AAPL" in order_confirmation
        assert user.balance == 700.00
        user = db_session.query(User).filter_by(username="user").one()
        user_portfolio = user.portfolios[0]
        assert user_portfolio.investments is not None
        investments = user_portfolio.investments
        assert len(investments) == 1
        investment = investments[0]
        assert investment.security.ticker == "AAPL"
        assert investment.quantity == 2
    except SecurityException:
        assert False, "Purchase order should not fail"

def test_place_purchase_order_insufficient_funds(db_session):
    _create_user(username="user", password="secret", firstname="Firstname", lastname="Lastname", balance=100.00)
    user = db_session.query(User).filter_by(username="user").one()
    assert user is not None
    _create_portfolio("Test Portfolio", "Test Portfolio Description", user)
    portfolio = db_session.query(Portfolio).filter_by(name="Test Portfolio").one()
    assert portfolio is not None
    try:
        set_logged_in_user(user)
        _execute_purchase_order(portfolio.id, "GOOGL", 1)
    except InsufficientFundsError as e:
        assert str(e) == "Insufficient funds to complete the purchase."
    else:
        assert False, "Expected InsufficientFundsError was not raised"

def test_build_securities_table(db_session):
    securities = get_all_securities()
    table: Table = build_securities_table(securities)
    assert table is not None
    assert len(table.rows) == 3
    tickers_in_table = table.columns[0]._cells
    assert "AAPL" in tickers_in_table
    assert "GOOGL" in tickers_in_table
    assert "MSFT" in tickers_in_table

def test_execute_order_for_no_logged_in_user(db_session):
    reset_logged_in_user()
    try:
        _execute_purchase_order(1, "AAPL", 1)
    except SecurityException as e:
        assert "No user is currently logged in." in str(e)
    else:
        assert False, "Expected SecurityException was not raised"

def test_execute_order_for_nonexistent_portfolio(db_session):
    _create_user(username="user", password="secret", firstname="Firstname", lastname="Lastname", balance=1000.00)
    user = db_session.query(User).filter_by(username="user").one()
    assert user is not None
    try:
        set_logged_in_user(user)
        _execute_purchase_order(999, "AAPL", 1)
    except SecurityException as e:
        assert "Portfolio with id 999 does not exist." in str(e)
    else:
        assert False, "Expected SecurityException was not raised"

def test_execute_order_for_nonexistent_security(db_session):
    _create_user(username="user", password="secret", firstname="Firstname", lastname="Lastname", balance=1000.00)
    user = db_session.query(User).filter_by(username="user").one()
    assert user is not None
    _create_portfolio("Test Portfolio", "Test Portfolio Description", user)
    portfolio = db_session.query(Portfolio).filter_by(name="Test Portfolio").one()
    assert portfolio is not None
    try:
        set_logged_in_user(user)
        _execute_purchase_order(portfolio.id, "INVALID", 1)
    except SecurityException as e:
        assert "Security with ticker INVALID does not exist." in str(e)
    else:
        assert False, "Expected SecurityException was not raised"

def test_exception_from_get_all_securities(db_session, monkeypatch):
    def mock_get_session_failure():
        raise Exception("Database connection error")
    monkeypatch.setattr('app.database.get_session', mock_get_session_failure)
    try:
        get_all_securities()
    except SecurityException as e:
        assert "Failed to retrieve securities due to error: Database connection error" in str(e)
    else:
        assert False, "Expected SecurityException was not raised"

def test_place_purchase_order(db_session, monkeypatch):
    def mock_input(dict):
        return {
            "portfolio_id": "1",
            "ticker": "AAPL",
            "quantity": "2"
        }
    monkeypatch.setattr('app.cli.input_collector.collect_inputs', mock_input)
    monkeypatch.setattr('app.service.security_service._execute_purchase_order', lambda portfolio_id, ticker, quantity: "Mocked purchase order executed")
    confirmation = place_purchase_order()
    assert confirmation == "Mocked purchase order executed"