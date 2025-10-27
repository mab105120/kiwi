from typing import List
from rich.table import Table
from domain import Security, Portfolio, Investment
from cli.input_collector import collect_inputs
from service.portfolio_service import add_investment_to_portfolio
from database import get_session
from session_state import get_logged_in_user

class SecurityException(Exception): pass
class InsufficientFundsError(Exception): pass

def get_all_securities() -> List[Security]:
    try:
        session = get_session()
        securities = session.query(Security).all()
        return securities
    except Exception as e:
        raise SecurityException(f"Failed to retrieve securities due to error: {str(e)}")
    finally:
        session.close() if session else None

def build_securities_table(securities: List[Security]) -> Table:
    table = Table(title="Securities")
    table.add_column("Ticker", style="cyan")
    table.add_column("Issuer")
    table.add_column("Price", justify="right", style="green")
    for security in securities:
        table.add_row(security.ticker, security.issuer, f"${security.price:.2f}")
    return table

def place_purchase_order() -> str: 
    user_inputs = collect_inputs({
        "Portfolio ID": "portfolio_id",
        "Ticker": "ticker",
        "Quantity": "quantity"
    })
    try:
        portfolio_id = int(user_inputs["portfolio_id"])
        ticker = user_inputs["ticker"]
        quantity = int(user_inputs["quantity"])
        return _execute_purchase_order(portfolio_id, ticker, quantity)
    except ValueError:
        raise SecurityException("Invalid input. Please try again.")

def _execute_purchase_order(portfolio_id: int, ticker: str, quantity: int) -> str:
    ''' Executes a purchase order for a given portfolio, ticker, and quantity.
        Raises SecurityException or InsufficientFundsError on failure.
    '''
    try:
        logged_in_user = get_logged_in_user()
        if not logged_in_user:
            raise SecurityException("No user is currently logged in.")
        session = get_session()
        portfolio = session.query(Portfolio).filter_by(id=portfolio_id).one_or_none()
        if not portfolio:
            raise SecurityException(f"Portfolio with id {portfolio_id} does not exist.")
        security = security = session.query(Security).filter_by(ticker=ticker).one_or_none()
        if not security:
            raise SecurityException(f"Security with ticker {ticker} does not exist.")
        
        total_cost = security.price * quantity
        if logged_in_user.balance < total_cost:
            raise InsufficientFundsError("Insufficient funds to complete the purchase.")

        add_investment_to_portfolio(portfolio, Investment(ticker=ticker, quantity=quantity))
        user = portfolio.user
        user.balance = logged_in_user.balance - total_cost
        logged_in_user.balance -= total_cost
        session.commit()
        return (
            f"Purchased {quantity} shares of {ticker} for ${total_cost:.2f}. "
            f"New balance: ${logged_in_user.balance:.2f}"
        )
    except InsufficientFundsError as e:
        session.rollback() if session else None
        raise e
    except Exception as e:
        session.rollback() if session else None
        raise SecurityException(f"Failed to execute purchase order due to error: {str(e)}")
    finally:
        session.close() if session else None