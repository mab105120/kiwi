import pytest

import app.service.portfolio_service as portfolio_service
from app.models import Portfolio, PortfolioSecurity, User


@pytest.fixture(autouse=True)
def setup(db_session):
    """Setup test data with users and portfolios."""
    user1 = User(
        username='user1',
        firstname='User',
        lastname='One',
        balance=1000.0,
    )
    user2 = User(
        username='user2',
        firstname='User',
        lastname='Two',
        balance=2000.0,
    )
    db_session.add_all([user1, user2])
    db_session.flush()

    portfolio1 = Portfolio(name='Portfolio 1', description='First portfolio', user=user1)
    portfolio2 = Portfolio(name='Portfolio 2', description='Second portfolio', user=user1)
    db_session.add_all([portfolio1, portfolio2])
    db_session.flush()

    return {
        'user1': user1,
        'user2': user2,
        'portfolio1': portfolio1,
        'portfolio2': portfolio2,
    }


def test_assign_portfolio_security(setup, db_session):
    """Test assigning a portfolio security role via service."""
    portfolio = setup['portfolio1']
    user = setup['user2']

    portfolio_service.assign_portfolio_security(portfolio.id, user.username, 'viewer')

    port_sec = (
        db_session.query(PortfolioSecurity).filter_by(portfolio_id=portfolio.id, username=user.username).one_or_none()
    )
    assert port_sec is not None
    assert port_sec.role == 'viewer'


def test_assign_portfolio_security_invalid_portfolio(setup, db_session):
    """Test assigning portfolio security with non-existent portfolio."""
    with pytest.raises(portfolio_service.PortfolioOperationError) as e:
        portfolio_service.assign_portfolio_security(9999, 'user2', 'viewer')
    assert 'Portfolio with id 9999 does not exist' in str(e.value)


def test_assign_portfolio_security_invalid_user(setup, db_session):
    """Test assigning portfolio security with non-existent user."""
    portfolio = setup['portfolio1']
    with pytest.raises(portfolio_service.PortfolioOperationError) as e:
        portfolio_service.assign_portfolio_security(portfolio.id, 'nonexistent_user', 'viewer')
    assert 'User with username nonexistent_user does not exist' in str(e.value)


def test_assign_multiple_users_same_portfolio(setup, db_session):
    """Test assigning multiple users to the same portfolio with different roles."""
    portfolio = setup['portfolio1']
    user1 = setup['user1']
    user2 = setup['user2']

    portfolio_service.assign_portfolio_security(portfolio.id, user1.username, 'admin')
    portfolio_service.assign_portfolio_security(portfolio.id, user2.username, 'editor')

    port_secs = db_session.query(PortfolioSecurity).filter_by(portfolio_id=portfolio.id).all()
    assert len(port_secs) == 2

    roles = {ps.username: ps.role for ps in port_secs}
    assert roles[user1.username] == 'admin'
    assert roles[user2.username] == 'editor'


def test_change_portfolio_security_role(setup, db_session):
    """Test changing the role of a portfolio security assignment."""
    portfolio = setup['portfolio1']
    user = setup['user2']

    portfolio_service.assign_portfolio_security(portfolio.id, user.username, 'viewer')
    portfolio_service.change_portfolio_security_role(portfolio.id, user.username, 'admin')

    port_sec = (
        db_session.query(PortfolioSecurity).filter_by(portfolio_id=portfolio.id, username=user.username).one_or_none()
    )
    assert port_sec.role == 'admin'


def test_change_portfolio_security_role_invalid(setup, db_session):
    """Test changing role for non-existent portfolio security."""
    portfolio = setup['portfolio1']
    user = setup['user2']

    with pytest.raises(portfolio_service.PortfolioOperationError) as e:
        portfolio_service.change_portfolio_security_role(portfolio.id, user.username, 'admin')
    assert 'PortfolioSecurity with portfolio_id' in str(e.value)


def test_remove_portfolio_security(setup, db_session):
    """Test removing a portfolio security assignment."""
    portfolio = setup['portfolio1']
    user = setup['user2']

    portfolio_service.assign_portfolio_security(portfolio.id, user.username, 'viewer')
    portfolio_service.remove_portfolio_security(portfolio.id, user.username)

    port_sec = (
        db_session.query(PortfolioSecurity).filter_by(portfolio_id=portfolio.id, username=user.username).one_or_none()
    )
    assert port_sec is None


def test_remove_portfolio_security_invalid(setup, db_session):
    """Test removing non-existent portfolio security."""
    portfolio = setup['portfolio1']
    user = setup['user2']

    with pytest.raises(portfolio_service.PortfolioOperationError) as e:
        portfolio_service.remove_portfolio_security(portfolio.id, user.username)
    assert 'PortfolioSecurity with portfolio_id' in str(e.value)


def test_portfolio_security_relationships(setup, db_session):
    """Test that relationships are properly loaded."""
    portfolio = setup['portfolio1']
    user = setup['user2']

    portfolio_service.assign_portfolio_security(portfolio.id, user.username, 'editor')

    port_sec = (
        db_session.query(PortfolioSecurity).filter_by(portfolio_id=portfolio.id, username=user.username).one_or_none()
    )

    assert port_sec.portfolio is not None
    assert port_sec.portfolio.id == portfolio.id
    assert port_sec.user is not None
    assert port_sec.user.username == user.username


def test_portfolio_security_to_dict(setup, db_session):
    """Test __to_dict__ method."""
    portfolio = setup['portfolio1']
    user = setup['user2']

    portfolio_service.assign_portfolio_security(portfolio.id, user.username, 'admin')

    port_sec = (
        db_session.query(PortfolioSecurity).filter_by(portfolio_id=portfolio.id, username=user.username).one_or_none()
    )

    result = port_sec.__to_dict__()
    assert result['portfolio_id'] == portfolio.id
    assert result['username'] == user.username
    assert result['role'] == 'admin'
    assert 'id' in result


def test_portfolio_security_str(setup, db_session):
    """Test __str__ method."""
    portfolio = setup['portfolio1']
    user = setup['user2']

    portfolio_service.assign_portfolio_security(portfolio.id, user.username, 'viewer')

    port_sec = (
        db_session.query(PortfolioSecurity).filter_by(portfolio_id=portfolio.id, username=user.username).one_or_none()
    )

    string_repr = str(port_sec)
    assert 'PortfolioSecurity' in string_repr
    assert str(portfolio.id) in string_repr
    assert user.username in string_repr
    assert 'viewer' in string_repr


def test_multiple_portfolio_securities_different_portfolios(setup, db_session):
    """Test assigning same user to different portfolios with different roles."""
    portfolio1 = setup['portfolio1']
    portfolio2 = setup['portfolio2']
    user = setup['user2']

    portfolio_service.assign_portfolio_security(portfolio1.id, user.username, 'admin')
    portfolio_service.assign_portfolio_security(portfolio2.id, user.username, 'viewer')

    port_secs = db_session.query(PortfolioSecurity).filter_by(username=user.username).all()
    assert len(port_secs) == 2

    roles = {ps.portfolio_id: ps.role for ps in port_secs}
    assert roles[portfolio1.id] == 'admin'
    assert roles[portfolio2.id] == 'viewer'
