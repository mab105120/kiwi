from typing import List
from app.models import Portfolio, Investment, User
import app.database as db
from app.service.user_service import update_user_balance
from app.service.transaction_service import record_transaction

class UnsupportedPortfolioOperationError(Exception): pass
class PortfolioOperationError(Exception): pass

def create_portfolio(name: str, description: str, user: User) -> int:
    session = None
    if not name or not description or not user:
        raise UnsupportedPortfolioOperationError(f"Invalid input[name:{name}, description: {description}, user: {user}]. Please try again.")
    portfolio = Portfolio(name=name, description=description, user=user)
    try:
        session = db.get_session()
        session.add(portfolio)
        session.commit()
        return portfolio.id
    except Exception as e:
        session.rollback() if session else None
        raise PortfolioOperationError(f"Failed to create portfolio due to error: {str(e)}")
    finally:
        session.close() if session else None

def get_portfolios_by_user(user: User) -> List[Portfolio]:
    session = None
    try:
        session = db.get_session()
        portfolios = session.query(Portfolio).filter_by(owner=user.username).all()
        return portfolios
    except Exception as e:
        session.rollback() if session else None
        raise PortfolioOperationError(f"Failed to retrieve portfolios due to error: {str(e)}")
    finally:
        session.close() if session else None

def get_all_portfolios() -> List[Portfolio]:
    session = None
    try:
        session = db.get_session()
        portfolios = session.query(Portfolio).all()
        return portfolios
    except Exception as e:
        session.rollback() if session else None
        raise PortfolioOperationError(f"Failed to retrieve portfolios due to error: {str(e)}")
    finally:
        session.close() if session else None

def get_portfolio_by_id(portfolio_id: int) -> Portfolio | None:
    session = None
    try:
        session = db.get_session()
        portfolio = session.query(Portfolio).filter_by(id=portfolio_id).one_or_none()
        return portfolio
    except Exception as e:
        session.rollback() if session else None
        raise PortfolioOperationError(f"Failed to retrieve portfolio due to error: {str(e)}")
    finally:
        session.close() if session else None

def delete_portfolio(portfolio_id: int):
    session = None
    try:
        session = db.get_session()
        portfolio = session.query(Portfolio).filter_by(id=portfolio_id).one_or_none()
        if not portfolio:
            raise UnsupportedPortfolioOperationError(f"Portfolio with id {portfolio_id} does not exist")
        session.delete(portfolio)
        session.commit()
    except Exception as e:
        session.rollback() if session else None
        raise e
    finally:
        session.close() if session else None

def liquidate_investment(portfolio_id: int, ticker: str, quantity: int, sale_price: float):
    session = None
    try:
        session = db.get_session()
        portfolio = session.query(Portfolio).filter_by(id=portfolio_id).one_or_none()
        if not portfolio:
            raise UnsupportedPortfolioOperationError(f"Portfolio with id {portfolio_id} does not exist")
        user = portfolio.user
        investment = next((inv for inv in portfolio.investments if inv.security.ticker == ticker), None)
        if not investment:
            raise UnsupportedPortfolioOperationError(f"No investment with ticker {ticker} exists in portfolio with id {portfolio_id}")
        if investment.quantity < quantity:
            raise UnsupportedPortfolioOperationError(f"Cannot liquidate {quantity} shares of {ticker}. Only {investment.quantity} shares available in portfolio")
        total_proceeds = sale_price * quantity
        user.balance += total_proceeds
        if investment.quantity == quantity:
            session.delete(investment)
        else:
            investment.quantity -= quantity
        session.commit()
        record_transaction(portfolio_id=portfolio.id, ticker=ticker, quantity=quantity, price=sale_price, transaction_type="SELL")
    except Exception as e:
        session.rollback() if session else None
        raise e
    finally:
        session.close() if session else None