import pytest
from app.cli.cli_wrapper_funcs import get_transactions_by_ticker, get_transactions_by_portfolio_id, _collect_inputs, create_portfolio, create_user, delete_portfolio, delete_user, get_portfolio_by_id, get_transactions_by_user, liquidate_investment, login, place_purchase_order
from app.models.User import User
from app.models.Portfolio import Portfolio
import app.service.portfolio_service as portfolio_service
import app.service.security_service as security_service
import app.service.user_service as user_service

def test_collect_inputs(monkeypatch):
    inputs = {
        "First Name": "first_name",
        "Last Name": "last_name",
        "Age": "age"
    }
    responses = iter(["John", "Doe", "30"])

    def mock_input(_, __):
        return next(responses)

    monkeypatch.setattr('rich.console.Console.input', mock_input)

    collected = _collect_inputs(inputs)
    assert collected == {
        "first_name": "John",
        "last_name": "Doe",
        "age": "30"
    }

def test_create_user(db_session,monkeypatch):
    inputs = {
        "username": "testuser",
        "password": "password123",
        "firstname": "Test",
        "lastname": "User",
        "balance": "1000"
    }
    monkeypatch.setattr('app.cli.cli_wrapper_funcs._collect_inputs', lambda _: inputs)
    result = create_user()
    assert result == "User testuser created successfully."

def test_create_user_invalid_balance(monkeypatch):
    inputs = {
        "username": "testuser",
        "password": "password123",
        "firstname": "Test",
        "lastname": "User",
        "balance": "invalid_number"
    }
    monkeypatch.setattr('app.cli.cli_wrapper_funcs._collect_inputs', lambda _: inputs)
    with pytest.raises(Exception) as e:
        create_user()
    assert str(e.value) == "Invalid input. Please try again."

def test_delete_user(db_session, monkeypatch):
    try:
        db_session.add(
            User(
                username='testuser',
                password='testpass',
                firstname='Test',
                lastname='User',
                balance=5000.00
            )
        )
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    username = "testuser"
    monkeypatch.setattr('app.cli.cli_wrapper_funcs._collect_inputs', lambda _: {"username": username})
    result = delete_user()
    deleted_user = db_session.query(User).filter_by(username=username).first()
    assert deleted_user is None
    assert result == f"User {username} deleted successfully"

def test_create_portfolio(db_session, monkeypatch):
    user = User(username='testuser',password='testpass',firstname='Test',lastname='User',balance=5000.00)
    try:
        db_session.add(user)
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    user = db_session.query(User).filter_by(username='testuser').one()
    assert user is not None
    assert len(user.portfolios) == 0
    inputs = {
        "name": "test_portfolio",
        "description": "test_portfolio_description"
    }
    monkeypatch.setattr('app.cli.cli_wrapper_funcs._collect_inputs', lambda _: inputs)
    monkeypatch.setattr('app.cli.session_state.get_logged_in_user', lambda: user)
    result = create_portfolio()
    user = db_session.query(User).filter_by(username='testuser').one()
    assert len(user.portfolios) == 1
    assert user.portfolios[0].name == "test_portfolio"
    assert result == "Created new portfolio test_portfolio"

def test_create_portfolio_no_user(monkeypatch):
    inputs = {
        "name": "test_portfolio",
        "description": "test_portfolio_description"
    }
    monkeypatch.setattr('app.cli.cli_wrapper_funcs._collect_inputs', lambda _: inputs)
    monkeypatch.setattr('app.cli.session_state.get_logged_in_user', lambda: None)
    with pytest.raises(Exception) as e:
        create_portfolio()
    assert str(e.value) == "Unexpected state encountered when creating portfolio. No user logged in"

def test_get_portfolio_by_id(db_session, monkeypatch):
    # create test user
    user= User(username='testuser',password='testpass',firstname='Test',lastname='User',balance=5000.00)
    db_session.add(user)
    db_session.commit()
    # create test portfolio
    portfolio_id = portfolio_service.create_portfolio('test_portfolio','test_description',user)
    # test getting portfolio
    inputs = {"portfolio_id": portfolio_id,}
    monkeypatch.setattr('app.cli.cli_wrapper_funcs._collect_inputs', lambda _: inputs)
    portfolio = get_portfolio_by_id()
    assert portfolio is not None
    assert portfolio.id == portfolio_id
    assert portfolio.name == 'test_portfolio'
    assert portfolio.description == 'test_description'
    # test getting invalid portfolio id
    inputs = {"portfolio_id": "invalid"}
    monkeypatch.setattr('app.cli.cli_wrapper_funcs._collect_inputs', lambda _: inputs)
    with pytest.raises(portfolio_service.UnsupportedPortfolioOperationError) as e:
        get_portfolio_by_id()
    assert "Invalid input. Please try again." in str(e.value)
    # test getting non-existent portfolio id
    inputs = {"portfolio_id": 9999}
    monkeypatch.setattr('app.cli.cli_wrapper_funcs._collect_inputs', lambda _: inputs)
    with pytest.raises(portfolio_service.UnsupportedPortfolioOperationError) as e:
        get_portfolio_by_id()
    assert "Portfolio with id 9999 does not exist" in str(e.value)

def test_delete_portfolio(db_session, monkeypatch):
    # create test user
    user= User(username='testuser',password='testpass',firstname='Test',lastname='User',balance=5000.00)
    db_session.add(user)
    db_session.commit()
    # create test portfolio
    portfolio_id = portfolio_service.create_portfolio('test_portfolio','test_description',user)
    # test deleting portfolio
    inputs = {"portfolio_id": portfolio_id,}
    monkeypatch.setattr('app.cli.cli_wrapper_funcs._collect_inputs', lambda _: inputs)
    result = delete_portfolio()
    deleted_portfolio = db_session.query(Portfolio).filter_by(id=portfolio_id).first()
    assert deleted_portfolio is None
    assert result == f"Deleted portfolio with id {portfolio_id}"
    # test deleting invalid portfolio id
    inputs = {"portfolio_id": "invalid"}
    monkeypatch.setattr('app.cli.cli_wrapper_funcs._collect_inputs', lambda _: inputs)
    with pytest.raises(portfolio_service.UnsupportedPortfolioOperationError) as e:
        delete_portfolio()
    assert "Invalid input. Please try again." in str(e.value)

def test_liquidate_investment(db_session, monkeypatch):
    monkeypatch.setattr('app.cli.session_state.get_logged_in_user', lambda: User(username='testuser'))
    monkeypatch.setattr('app.service.portfolio_service.liquidate_investment', lambda portfolio_id, ticker, quantity, sale_price: None)
    inputs = {
        "portfolio_id": "1",
        "ticker": "AAPL",
        "quantity": "10",
        "sale_price": "150.00"
    }
    monkeypatch.setattr('app.cli.cli_wrapper_funcs._collect_inputs', lambda _: inputs)
    results = liquidate_investment()
    assert results == "Liquidated 10 shares of AAPL from portfolio with id 1."

def test_liquidate_investment_invalid_input(monkeypatch):
    monkeypatch.setattr('app.cli.session_state.get_logged_in_user', lambda: User(username='testuser'))
    inputs = {
        "portfolio_id": "invalid",
        "ticker": "AAPL",
        "quantity": "10",
        "sale_price": "150.00"
    }
    monkeypatch.setattr('app.cli.cli_wrapper_funcs._collect_inputs', lambda _: inputs)
    with pytest.raises(portfolio_service.UnsupportedPortfolioOperationError) as e:
        liquidate_investment()
    assert "Invalid input. Please try again." in str(e.value)

def test_liquidate_investment_no_user(monkeypatch):
    monkeypatch.setattr('app.cli.session_state.get_logged_in_user', lambda: None)
    inputs = {
        "portfolio_id": "1",
        "ticker": "AAPL",
        "quantity": "10",
        "sale_price": "150.00"
    }
    monkeypatch.setattr('app.cli.cli_wrapper_funcs._collect_inputs', lambda _: inputs)
    with pytest.raises(Exception) as e:
        liquidate_investment()
    assert str(e.value) == "No user is currently logged in"

def test_place_purchase_order(monkeypatch):
    monkeypatch.setattr('app.service.security_service.execute_purchase_order', lambda portfolio_id, ticker, quantity: None)
    inputs = {"portfolio_id": "1","ticker": "AAPL","quantity": "10"}
    monkeypatch.setattr('app.cli.cli_wrapper_funcs._collect_inputs', lambda _: inputs)
    result = place_purchase_order()
    assert result == "Purchased 10 shares of AAPL"
    inputs = {"portfolio_id": "1","ticker": "AAPL","quantity": "10s"}
    with pytest.raises(security_service.SecurityException) as e:
        monkeypatch.setattr('app.cli.cli_wrapper_funcs._collect_inputs', lambda _: inputs)
        place_purchase_order()
    assert "Invalid input. Please try again." in str(e.value)

def test_get_transactions_by_user(monkeypatch):
    user = User(username='testuser')
    monkeypatch.setattr('app.cli.session_state.get_logged_in_user', lambda: user)
    monkeypatch.setattr('app.service.transaction_service.get_transactions_by_user', lambda username: ["transaction1","transaction2"])
    transactions = get_transactions_by_user()
    assert transactions == ["transaction1","transaction2"]
    # test for non logged in user
    monkeypatch.setattr('app.cli.session_state.get_logged_in_user', lambda: None)
    with pytest.raises(user_service.UnsupportedUserOperationError) as e:
        get_transactions_by_user()
    assert str(e.value) == "No user is currently logged in"


def test_get_transactions_by_portfolio_id(monkeypatch):
    inputs = {"portfolio_id": "1"}
    monkeypatch.setattr('app.cli.cli_wrapper_funcs._collect_inputs', lambda _: inputs)
    monkeypatch.setattr('app.service.transaction_service.get_transactions_by_portfolio_id', lambda portfolio_id: ["transactionA","transactionB"])
    transactions = get_transactions_by_portfolio_id()
    assert transactions == ["transactionA","transactionB"]
    # test for invalid portfolio id
    inputs = {"portfolio_id": "invalid"}
    monkeypatch.setattr('app.cli.cli_wrapper_funcs._collect_inputs', lambda _: inputs)
    with pytest.raises(user_service.UnsupportedUserOperationError) as e:
        get_transactions_by_portfolio_id()
    assert "Invalid input. Please try again." in str(e.value)

def test_get_transactions_by_ticker(monkeypatch):
    inputs = {"ticker": "AAPL"}
    monkeypatch.setattr('app.cli.cli_wrapper_funcs._collect_inputs', lambda _: inputs)
    monkeypatch.setattr('app.service.transaction_service.get_transactions_by_ticker', lambda ticker: ["transactionX","transactionY"])
    transactions = get_transactions_by_ticker()
    assert transactions == ["transactionX","transactionY"]

def test_login(monkeypatch):
    inputs = {"username": "testuser","password": "testpass"}
    monkeypatch.setattr('app.cli.cli_wrapper_funcs._collect_inputs', lambda _: inputs)
    monkeypatch.setattr('app.service.login_service.login', lambda username, password: User(username='testuser'))
    login()
    