from typing import List
from rich.table import Table
from sqlalchemy.orm import selectinload
import app.session_state as session_state
import app.cli.input_collector as collector
from app.domain import Portfolio, Investment, User
import app.database as db
from app.service.user_service import update_user_balance

class UnsupportedPortfolioOperationError(Exception): pass
class PortfolioOperationError(Exception): pass

def create_portfolio() -> str:
    user_inputs = collector.collect_inputs({
        "Portfolio name": "name",
        "Portfolio description": "description" 
    })
    name = user_inputs["name"]
    description = user_inputs["description"]
    user = session_state.get_logged_in_user()
    if not user:
        raise Exception("Unexpected state encountered when creating portfolio. No user logged in")
    return _create_portfolio(name, description, user)

def _create_portfolio(name: str, description: str, user: User) -> str:
    session = None
    portfolio = Portfolio(name=name, description=description, user=user)
    try:
        session = db.get_session()
        session.add(portfolio)
        session.commit()
        return f"Created new portfolio {name}"
    except Exception as e:
        session.rollback() if session else None
        raise PortfolioOperationError(f"Failed to create portfolio due to error: {str(e)}")
    finally:
        session.close() if session else None

def get_all_portfolios() -> List[Portfolio]:
    session = None
    try:
        session = db.get_session()
        portfolios = session.query(Portfolio).options(selectinload(Portfolio.investments).selectinload(Investment.security)).all()
        return portfolios
    except Exception as e:
        session.rollback() if session else None
        raise PortfolioOperationError(f"Failed to retrieve portfolios due to error: {str(e)}")
    finally:
        session.close() if session else None

def build_portfolios_table(portfolios: List[Portfolio]) -> Table|str:
    if len(portfolios) == 0:
        return "No portfolios exist. Add new portfolios"
    table = Table(title="Portfolios")
    table.add_column("Id")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Value", justify="right", style="green")
    for portfolio in portfolios:
        table.add_row(str(portfolio.id), portfolio.name, portfolio.description, f"${portfolio.get_portfolio_value():.2f}")
    return table

def build_portfolio_investments_table() -> Table:
    session = None
    try:
        session = db.get_session()
        portfolio_id = int(collector.collect_inputs({"Portfolio ID to view investments": "portfolio_id"})["portfolio_id"])
        portfolio = session.query(Portfolio).filter_by(id=portfolio_id).one_or_none()
        
        if not portfolio:
            raise UnsupportedPortfolioOperationError(f"Portfolio with id {portfolio_id} does not exist")
        if len(portfolio.investments) == 0:
            raise UnsupportedPortfolioOperationError(f"No investments exist in portfolio with id {portfolio_id}")
        table = Table(title=f"Investments in Portfolio {portfolio.name} (ID: {portfolio.id})")
        table.add_column("Ticker", style="cyan")
        table.add_column("Issuer")
        table.add_column("Quantity", justify="right")
        table.add_column("Price", justify="right", style="green")
        table.add_column("Total Value", justify="right", style="green")
        for investment in portfolio.investments:
            total_value = investment.quantity * investment.security.price
            table.add_row(investment.security.ticker, investment.security.issuer, str(investment.quantity), f"${investment.security.price:.2f}", f"${total_value:.2f}")
        return table
    except ValueError:
        session.rollback() if session else None
        raise UnsupportedPortfolioOperationError("Invalid input. Please try again.")
    except Exception as e:
        session.rollback() if session else None
        raise e
    finally:
        session.close() if session else None


def delete_portfolio() -> str:
    session = None
    try:
        portfolio_id = int(collector.collect_inputs({"Portfolio ID to delete": "portfolio_id"})["portfolio_id"])
        session = db.get_session()
        portfolio = session.query(Portfolio).filter_by(id=portfolio_id).one_or_none()

        if not portfolio:
            raise UnsupportedPortfolioOperationError(f"Portfolio with id {portfolio_id} does not exist")
        session.delete(portfolio)
        session.commit()
        return f"Deleted portfolio with id {portfolio_id}"
    except ValueError:
        session.rollback() if session else None
        raise UnsupportedPortfolioOperationError("Invalid input. Please try again.")
    except Exception as e:
        session.rollback() if session else None
        raise e
    finally:
        session.close() if session else None

def add_investment_to_portfolio(portfolio: Portfolio, investment: Investment):
    for existing_investment in portfolio.investments:
        if existing_investment.ticker == investment.ticker:
            existing_investment.quantity += investment.quantity
            return
    portfolio.investments.append(investment)

def liquidate_investment() -> str:
    session = None
    try:
        user_inputs = collector.collect_inputs({
            "Portfolio ID": "portfolio_id",
            "Ticker": "ticker",
            "Quantity": "quantity",
            "Sale price": "sale_price"
        })
        portfolio_id = int(user_inputs["portfolio_id"])
        ticker = user_inputs["ticker"]
        quantity = int(user_inputs["quantity"])
        sale_price = float(user_inputs["sale_price"])

        session = db.get_session()
        portfolio = session.query(Portfolio).filter_by(id=portfolio_id).one_or_none()

        if not portfolio:
            raise UnsupportedPortfolioOperationError(f"Portfolio with id {portfolio_id} does not exist")
        investment = next((inv for inv in portfolio.investments if inv.security.ticker == ticker), None)
        if not investment:
            raise UnsupportedPortfolioOperationError(f"No investment with ticker {ticker} exists in portfolio with id {portfolio_id}")
        if investment.quantity < quantity:
            raise UnsupportedPortfolioOperationError(f"Cannot liquidate {quantity} shares of {ticker}. Only {investment.quantity} shares available in portfolio")
        total_proceeds = sale_price * quantity
        logged_in_user = session_state.get_logged_in_user()
        if not logged_in_user:
            raise Exception("Unexpected state encountered when liquidating investment. No user logged in")
        update_user_balance(logged_in_user.username, logged_in_user.balance + total_proceeds)
        if investment.quantity == quantity:
            session.delete(investment)
        else:
            investment.quantity -= quantity
        session.commit()
        return f"Liquidated {quantity} shares of {ticker} from portfolio with id {portfolio_id}. Added ${total_proceeds:.2f} to user balance"
    except ValueError:
        session.rollback() if session else None
        raise UnsupportedPortfolioOperationError("Invalid input. Please try again.")
    except Exception as e:
        session.rollback() if session else None
        raise e
    finally:
        session.close() if session else None