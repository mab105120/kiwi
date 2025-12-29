import pytest
from app.service.portfolio_service import _create_portfolio, add_investment_to_portfolio, build_portfolio_investments_table, build_portfolios_table, create_portfolio, delete_portfolio, get_all_portfolios, liquidate_investment, UnsupportedPortfolioOperationError
from app.session_state import reset_logged_in_user, set_logged_in_user
from app.domain import Investment, Portfolio, User, Security

def test_create_portfolio_input(db_session, monkeypatch):
    set_logged_in_user(User(username="testuser", balance=1000.0))
    monkeypatch.setattr("app.cli.input_collector.collect_inputs", lambda _: {"name": "Test Portfolio", "description": "A test portfolio"})
    monkeypatch.setattr("app.service.portfolio_service._create_portfolio", lambda name, description, user: f"Created new portfolio {name}")
    result = create_portfolio()
    assert result == "Created new portfolio Test Portfolio"
    reset_logged_in_user()
    try:
        create_portfolio()
    except Exception as e:
        assert str(e) == "Unexpected state encountered when creating portfolio. No user logged in"

def test_create_portfolio(db_session):
    user = User(username="testuser", password="testpass", firstname="Test", lastname="User", balance=1000.0)
    db_session.add(user)
    db_session.commit()
    result = _create_portfolio("My Portfolio", "This is my portfolio", user)
    assert "Created new portfolio My Portfolio" in result
    portfolios = db_session.query(Portfolio).filter_by(name="My Portfolio").all()
    assert len(portfolios) == 1
    assert portfolios[0].description == "This is my portfolio"
    assert portfolios[0].user.username == "testuser"

def test_create_portfolio_db_failure(monkeypatch):
    def failing_get_session():
        raise Exception("Database connection error")
    monkeypatch.setattr("app.database.get_session", failing_get_session)
    try:
        _create_portfolio("Fail Portfolio", "This should fail", None)
    except Exception as e:
        assert "Failed to create portfolio due to error: Database connection error" in str(e)

def test_get_all_portfolios(db_session):
    user = User(username="testuser", password="testpass", firstname="Test", lastname="User", balance=1000.0)
    db_session.add(user)
    db_session.commit()
    portfolio1 = Portfolio(name="Portfolio 1", description="First portfolio", user=user)
    portfolio2 = Portfolio(name="Portfolio 2", description="Second portfolio", user=user)
    db_session.add_all([portfolio1, portfolio2])
    db_session.commit()
    portfolios = get_all_portfolios()
    assert len(portfolios) >= 2
    names = [p.name for p in portfolios]
    assert "Portfolio 1" in names
    assert "Portfolio 2" in names

def test_get_all_portfolios_db_failure(monkeypatch):
    def failing_get_session():
        raise Exception("Database connection error")
    monkeypatch.setattr("app.database.get_session", failing_get_session)
    try:
        get_all_portfolios()
    except Exception as e:
        assert "Failed to retrieve portfolios due to error: Database connection error" in str(e)

def test_build_portfolios_table():
    result = build_portfolios_table([])
    assert result == "No portfolios exist. Add new portfolios"
    table = build_portfolios_table([Portfolio(id=1, name="Portfolio 1", description="Desc 1"),
                                     Portfolio(id=2, name="Portfolio 2", description="Desc 2")])
    assert table is not None
    assert table.title == "Portfolios"
    assert type(table) != str

def test_build_portfolio_investments_table(db_session, monkeypatch):
    user = User(username="testuser", password="testpass", firstname="Test", lastname="User", balance=100000.0)
    db_session.add(user)
    db_session.commit()
    portfolio = Portfolio(name="Portfolio 1", description="Desc 1", user=user)
    db_session.add(portfolio)
    add_investment_to_portfolio(portfolio, Investment(ticker="AAPL", quantity=10))
    db_session.commit()
    monkeypatch.setattr("app.cli.input_collector.collect_inputs", lambda _: {"portfolio_id": str(portfolio.id)})
    table = build_portfolio_investments_table()
    assert table is not None
    assert table.title == f"Investments in Portfolio {portfolio.name} (ID: {portfolio.id})"

def test_build_portfolio_invalid_portfolio_id(db_session, monkeypatch):
    monkeypatch.setattr("app.cli.input_collector.collect_inputs", lambda _: {"portfolio_id": "9999"})
    try:
        build_portfolio_investments_table()
    except Exception as e:
        assert "Portfolio with id 9999 does not exist" in str(e)

def test_build_portfolio_table_with_no_investments(db_session, monkeypatch):
    user = User(username="testuser", password="testpass", firstname="Test", lastname="User", balance=100000.0)
    db_session.add(user)
    db_session.commit()
    portfolio = Portfolio(name="Empty Portfolio", description="No investments here", user=user)
    db_session.add(portfolio)
    db_session.commit()
    monkeypatch.setattr("app.cli.input_collector.collect_inputs", lambda _: {"portfolio_id": str(portfolio.id)})
    try:
        build_portfolio_investments_table()
    except Exception as e:
        assert "No investments exist in portfolio" in str(e)

def test_build_portfolio_with_invalid_input(monkeypatch):
    monkeypatch.setattr("app.cli.input_collector.collect_inputs", lambda _: {"portfolio_id": "invalid"})
    try:
        build_portfolio_investments_table()
    except Exception as e:
        assert "Invalid input. Please try again." in str(e)

def test_delete_portfolio(db_session, monkeypatch):
    user = User(username="testuser", password="testpass", firstname="Test", lastname="User", balance=100000.0)
    db_session.add(user)
    db_session.commit()
    portfolio = Portfolio(name="To Be Deleted", description="This portfolio will be deleted", user=user)
    db_session.add(portfolio)
    db_session.commit()
    monkeypatch.setattr("app.cli.input_collector.collect_inputs", lambda _: {"portfolio_id": str(portfolio.id)})
    result = delete_portfolio()
    assert f"Deleted portfolio with id {portfolio.id}" in result
    deleted_portfolio = db_session.query(Portfolio).filter_by(id=portfolio.id).one_or_none()
    assert deleted_portfolio is None

def test_delete_portfolio_invalid_id(db_session, monkeypatch):
    monkeypatch.setattr("app.cli.input_collector.collect_inputs", lambda _: {"portfolio_id": "9999"})
    try:
        delete_portfolio()
    except Exception as e:
        assert "Portfolio with id 9999 does not exist" in str(e)

def test_delete_portfolio_invalid_input(monkeypatch):
    monkeypatch.setattr("app.cli.input_collector.collect_inputs", lambda _: {"portfolio_id": "invalid"})
    try:
        delete_portfolio()
    except Exception as e:
        assert "Invalid input. Please try again." in str(e)

def test_add_investment_to_portfolio():
    portfolio = Portfolio(name="Test Portfolio", description="Testing investments")
    investment1 = Investment(ticker="AAPL", quantity=10)
    investment2 = Investment(ticker="AAPL", quantity=5)
    investment3 = Investment(ticker="GOOGL", quantity=8)
    add_investment_to_portfolio(portfolio, investment1)
    assert len(portfolio.investments) == 1
    assert portfolio.investments[0].quantity == 10
    add_investment_to_portfolio(portfolio, investment2)
    assert len(portfolio.investments) == 1
    assert portfolio.investments[0].quantity == 15
    add_investment_to_portfolio(portfolio, investment3)
    assert len(portfolio.investments) == 2
    quantities = {inv.ticker: inv.quantity for inv in portfolio.investments}
    assert quantities["AAPL"] == 15
    assert quantities["GOOGL"] == 8

def test_liquidate_investment(db_session, monkeypatch):
    user = User(username="testuser", password="testpass", firstname="Test", lastname="User", balance=100000.0)
    db_session.add(user)
    db_session.commit()
    monkeypatch.setattr("app.session_state.get_logged_in_user", lambda: user)
    portfolio = Portfolio(name="Investment Portfolio", description="Portfolio for liquidation test", user=user)
    db_session.add(portfolio)
    aapl_security = db_session.query(Security).filter_by(ticker="AAPL").one_or_none()
    assert aapl_security is not None
    investment = Investment(ticker="AAPL", quantity=20, security=aapl_security)
    add_investment_to_portfolio(portfolio, investment)
    db_session.commit()
    monkeypatch.setattr("app.cli.input_collector.collect_inputs", lambda _: {
        "portfolio_id": str(portfolio.id),
        "ticker": "AAPL",
        "quantity": "5",
        "sale_price": "150.0"
    })
    result = liquidate_investment()
    assert "Liquidated 5 shares of AAPL from portfolio with id" in result
    updated_investment = next((inv for inv in portfolio.investments if inv.ticker == "AAPL"), None)
    assert updated_investment is not None
    assert updated_investment.quantity == 15
    updated_user = db_session.query(User).filter_by(username="testuser").one()
    assert updated_user.balance == 100000.0 + (5 * 150.0)

def test_liquidate_investment_invalid_portfolio(db_session, monkeypatch):
    monkeypatch.setattr("app.session_state.get_logged_in_user", lambda: User(username="testuser", balance=100000.0))
    monkeypatch.setattr("app.cli.input_collector.collect_inputs", lambda _: {
        "portfolio_id": "9999",
        "ticker": "AAPL",
        "quantity": "5",
        "sale_price": "150.0"
    })
    try:
        liquidate_investment()
    except Exception as e:
        assert "Portfolio with id 9999 does not exist" in str(e)

def test_liquidate_non_existing_investment(db_session, monkeypatch):
    user = User(username="testuser", password="testpass", firstname="Test", lastname="User", balance=100000.0)
    db_session.add(user)
    db_session.commit()
    portfolio = Portfolio(name="Empty Portfolio", description="No investments here", user=user)
    db_session.add(portfolio)
    db_session.commit()
    monkeypatch.setattr("app.session_state.get_logged_in_user", lambda: user)
    monkeypatch.setattr("app.cli.input_collector.collect_inputs", lambda _: {
        "portfolio_id": str(portfolio.id),
        "ticker": "AAPL",
        "quantity": "5",
        "sale_price": "150.0"
    })
    with pytest.raises(UnsupportedPortfolioOperationError):
        liquidate_investment()