import pytest

import app.service.portfolio_service as portfolio_service
import app.service.transaction_service as transaction_service
from app.db import db
from app.models import Investment, Portfolio, User


@pytest.fixture(autouse=True)
def setup(db_session):
    user = User(
        username='testuser',
        firstname='Test',
        lastname='User',
        balance=1000.0,
    )
    db_session.add(user)
    db_session.commit()
    portfolio1 = Portfolio(name='Portfolio 1', description='First portfolio', user=user)
    portfolio2 = Portfolio(name='Portfolio 2', description='Second portfolio', user=user)
    db_session.add_all([portfolio1, portfolio2])
    portfolio1.investments.append(Investment(ticker='AAPL', quantity=10))
    db_session.commit()
    return {'user': user, 'portfolio1': portfolio1, 'portfolio2': portfolio2}


def test_get_portfolios_by_user_db_failure(db_session, monkeypatch):
    def failing_get_session(_):
        raise Exception('Database query error')

    monkeypatch.setattr(db_session, 'query', failing_get_session)
    with pytest.raises(Exception) as e:
        portfolio_service.get_portfolios_by_user(User(username='testuser', firstname='', lastname='', balance=0.0))
    assert 'Failed to retrieve portfolios due to error: Database query error' in str(e.value)


def test_get_all_portfolios(db_session):
    portfolios = portfolio_service.get_all_portfolios()
    assert len(portfolios) >= 2
    names = [p.name for p in portfolios]
    assert 'Portfolio 1' in names
    assert 'Portfolio 2' in names


def test_get_all_portfolios_db_failure(db_session, monkeypatch):
    def failing_query(_):
        raise Exception('Database connection error')

    monkeypatch.setattr(db_session, 'query', failing_query)
    with pytest.raises(Exception) as e:
        portfolio_service.get_all_portfolios()
    assert 'Failed to retrieve portfolios due to error: Database connection error' in str(e.value)


def test_get_portfolio_by_id(setup, db_session):
    portfolio = setup['portfolio1']
    retrieved_portfolio = portfolio_service.get_portfolio_by_id(portfolio.id)
    assert retrieved_portfolio is not None
    assert retrieved_portfolio.name == 'Portfolio 1'
    assert retrieved_portfolio.description == 'First portfolio'


def test_get_portfolio_by_id_db_failure(db_session, monkeypatch):
    def failing_get_session(_):
        raise Exception('Database connection error')

    monkeypatch.setattr(db_session, 'query', failing_get_session)
    with pytest.raises(Exception) as e:
        portfolio_service.get_portfolio_by_id(1)
    assert 'Failed to retrieve portfolio due to error: Database connection error' in str(e.value)


def test_get_portfolio_by_invalid_id(db_session):
    invalid_id = 9999
    assert portfolio_service.get_portfolio_by_id(invalid_id) is None


def test_create_portfolio(setup, db_session):
    user = setup['user']
    user_portfolios_before = portfolio_service.get_portfolios_by_user(user)
    assert len(user_portfolios_before) == 2
    portfolio_service.create_portfolio('Test Portfolio', 'A test portfolio', user)
    user_portfolios_after = portfolio_service.get_portfolios_by_user(user)
    assert len(user_portfolios_after) == 3
    assert user_portfolios_after[-1].name == 'Test Portfolio'
    assert user_portfolios_after[-1].description == 'A test portfolio'


def test_create_portfolio_invalid_input():
    user = User(
        username='testuser',
        firstname='Test',
        lastname='User',
        balance=1000.0,
    )
    with pytest.raises(portfolio_service.UnsupportedPortfolioOperationError):
        portfolio_service.create_portfolio('', 'A test portfolio', user)
    with pytest.raises(portfolio_service.UnsupportedPortfolioOperationError):
        portfolio_service.create_portfolio('Test Portfolio', '', user)


def test_create_portfolio_db_failure(db_session, monkeypatch):
    def failing_add(_):
        raise Exception('Database connection error')

    monkeypatch.setattr(db_session, 'add', failing_add)
    with pytest.raises(Exception) as e:
        portfolio_service.create_portfolio(
            'Fail Portfolio',
            'This should fail',
            User(username='testuser', firstname='', lastname='', balance=0.0),
        )
    assert 'Failed to create portfolio due to error: Database connection error' in str(e.value)


def test_delete_portfolio(setup, db_session):
    user = setup['user']
    portfolio = Portfolio(name='To Be Deleted', description='This portfolio will be deleted', user=user)
    db_session.add(portfolio)
    db_session.commit()
    portfolio_service.delete_portfolio(portfolio.id)
    deleted_portfolio = db_session.query(Portfolio).filter_by(id=portfolio.id).one_or_none()
    assert deleted_portfolio is None


def test_delete_portfolio_invalid_id(db_session):
    with pytest.raises(Exception):
        portfolio_service.delete_portfolio(9999)


def test_liquidate_investment(setup, db_session, mock_alpha_vantage):
    portfolio = setup['portfolio1']
    portfolio_service.liquidate_investment(portfolio.id, 'AAPL', 5)
    portfolio = db_session.query(Portfolio).filter_by(id=portfolio.id).one()
    updated_investment = next((inv for inv in portfolio.investments if inv.ticker == 'AAPL'), None)
    assert updated_investment is not None
    assert updated_investment.quantity == 5
    user = db_session.query(User).filter_by(username='testuser').one()
    assert user.balance == 1000.0 + (5 * 150.0)


def test_liquidate_entire_investment(setup, db_session, mock_alpha_vantage):
    portfolio = setup['portfolio1']
    portfolio_service.liquidate_investment(portfolio.id, 'AAPL', 10)
    db_session.refresh(portfolio)
    portfolio = db_session.query(Portfolio).filter_by(id=portfolio.id).one()
    updated_investment = next((inv for inv in portfolio.investments if inv.ticker == 'AAPL'), None)
    assert updated_investment is None
    user = db_session.query(User).filter_by(username='testuser').one()
    assert user.balance == 1000.0 + (10 * 150.0)


def test_liquidate_investment_invalid_portfolio(db_session, mock_alpha_vantage):
    with pytest.raises(portfolio_service.PortfolioOperationError):
        portfolio_service.liquidate_investment(9999, 'AAPL', 5)


def test_liquidate_non_existing_investment(setup, db_session, mock_alpha_vantage):
    portfolio = setup['portfolio1']
    with pytest.raises(portfolio_service.PortfolioOperationError):
        portfolio_service.liquidate_investment(portfolio.id, 'MSFT', 5)


def test_liquidate_investment_insufficient_quantity(setup, db_session, mock_alpha_vantage):
    portfolio = setup['portfolio1']
    with pytest.raises(portfolio_service.PortfolioOperationError) as e:
        portfolio_service.liquidate_investment(portfolio.id, 'AAPL', 1000)
    assert 'Cannot liquidate 1000 shares of AAPL. Only 10 shares available in portfolio' in str(e.value)


def test_liquidate_investment_quote_unavailable(setup, db_session, monkeypatch):
    """Test liquidation fails when market data is unavailable."""
    import app.service.alpha_vantage_client as alpha_vantage_client

    # Mock get_quote to return None (API failure/unavailable)
    monkeypatch.setattr(alpha_vantage_client, 'get_quote', lambda _: None)

    portfolio = setup['portfolio1']
    with pytest.raises(portfolio_service.PortfolioOperationError) as e:
        portfolio_service.liquidate_investment(portfolio.id, 'AAPL', 5)
    assert 'Unable to fetch current price for AAPL from market data provider' in str(e.value)


def test_execute_purchase_order_success(setup, db_session, mock_alpha_vantage):
    """Test successful purchase order execution"""
    portfolio = setup['portfolio2']
    user = setup['user']
    initial_balance = user.balance

    portfolio_service.execute_purchase_order(portfolio.id, 'AAPL', 5)

    db_session.expire_all()
    user_after = db_session.query(User).filter_by(username='testuser').one()
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
    portfolio = setup['portfolio2']

    # First purchase: 5 shares at $150 = $750, leaving $250
    portfolio_service.execute_purchase_order(portfolio.id, 'AAPL', 5)
    # Second purchase: 1 share at $150 = $150, leaving $100
    portfolio_service.execute_purchase_order(portfolio.id, 'AAPL', 1)

    db_session.expire_all()
    portfolio_after = db_session.query(Portfolio).filter_by(id=portfolio.id).one()
    assert len(portfolio_after.investments) == 1
    assert portfolio_after.investments[0].quantity == 6


def test_execute_purchase_order_insufficient_funds(setup, db_session, mock_alpha_vantage):
    """Test purchase order fails with insufficient funds"""
    portfolio = setup['portfolio2']

    with pytest.raises(Exception) as e:
        portfolio_service.execute_purchase_order(portfolio.id, 'AAPL', 1000)
    assert 'Insufficient funds' in str(e.value)


def test_execute_purchase_order_invalid_portfolio(db_session, mock_alpha_vantage):
    """Test purchase order fails with non-existent portfolio"""
    with pytest.raises(portfolio_service.PortfolioOperationError) as e:
        portfolio_service.execute_purchase_order(9999, 'AAPL', 5)
    assert 'Portfolio with id 9999 does not exist' in str(e.value)


def test_execute_purchase_order_invalid_ticker(setup, db_session, mock_alpha_vantage):
    """Test purchase order fails with non-existent ticker"""
    portfolio = setup['portfolio2']

    with pytest.raises(portfolio_service.PortfolioOperationError) as e:
        portfolio_service.execute_purchase_order(portfolio.id, 'NONEXISTENT', 5)
    assert 'does not exist or market data unavailable' in str(e.value)


def test_execute_purchase_order_invalid_parameters(setup, db_session, mock_alpha_vantage):
    """Test purchase order validation"""
    portfolio = setup['portfolio2']

    # None portfolio_id
    with pytest.raises(portfolio_service.PortfolioOperationError) as e:
        portfolio_service.execute_purchase_order(None, 'AAPL', 5)  # type: ignore
    assert 'Invalid purchase order parameters' in str(e.value)

    # Empty ticker
    with pytest.raises(portfolio_service.PortfolioOperationError) as e:
        portfolio_service.execute_purchase_order(portfolio.id, '', 5)
    assert 'Invalid purchase order parameters' in str(e.value)

    # Zero quantity
    with pytest.raises(portfolio_service.PortfolioOperationError) as e:
        portfolio_service.execute_purchase_order(portfolio.id, 'AAPL', 0)
    assert 'Invalid purchase order parameters' in str(e.value)

    # Negative quantity
    with pytest.raises(portfolio_service.PortfolioOperationError) as e:
        portfolio_service.execute_purchase_order(portfolio.id, 'AAPL', -5)
    assert 'Invalid purchase order parameters' in str(e.value)


def test_execute_purchase_order_portfolio_without_user(setup, app, db_session, mock_alpha_vantage, monkeypatch):
    """Test purchase order fails when portfolio has no associated user"""
    portfolio = setup['portfolio2']

    # Mock the query to return a portfolio without a user
    def mock_query_portfolio(_):
        class MockQuery:
            def filter_by(self, **kwargs):
                return self

            def one_or_none(self):
                mock_portfolio = Portfolio(name='Orphan Portfolio', description='No user')
                mock_portfolio.id = portfolio.id
                mock_portfolio.user = None  # type: ignore
                mock_portfolio.investments = []
                return mock_portfolio

        return MockQuery()

    monkeypatch.setattr(db.session, 'query', mock_query_portfolio)

    with pytest.raises(portfolio_service.PortfolioOperationError) as e:
        portfolio_service.execute_purchase_order(portfolio.id, 'AAPL', 5)
    assert f'User associated with the portfolio ({portfolio.id}) does not exist' in str(e.value)
