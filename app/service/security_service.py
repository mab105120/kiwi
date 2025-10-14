from typing import List
from rich.table import Table
from domain.Security import Security
from domain.Investment import Investment
from cli.input_collector import collect_inputs
from service.portfolio_service import add_investment_to_portfolio
import db

class SecurityException(Exception):
    def __init__(self, message: str):
        super().__init__(message)

class InsufficientFundsError(Exception): pass

def get_all_securities() -> List[Security]:
    return db.get_all_securities()

def print_all_securities(securities: List[Security]) -> Table:
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
        return execute_purchase_order(portfolio_id, ticker, quantity)
    except ValueError:
        raise SecurityException("Invalid input. Please try again.")


def execute_purchase_order(portfolio_id: int, ticker: str, quantity: int) -> str:
    logged_in_user = db.get_logged_in_user()
    if not logged_in_user:
        raise SecurityException("No user is currently logged in.")

    portfolio = db.get_portfolio_by_id(portfolio_id)
    if not portfolio:
        raise SecurityException(f"Portfolio with id {portfolio_id} does not exist.")

    security = next((s for s in db.get_all_securities() if s.ticker == ticker), None)
    if not security:
        raise SecurityException(f"Security with ticker {ticker} does not exist.")

    total_cost = security.price * quantity
    if logged_in_user.balance < total_cost:
        raise InsufficientFundsError("Insufficient funds to complete the purchase.")

    add_investment_to_portfolio(portfolio, Investment(security, quantity))
    logged_in_user.balance -= total_cost

    return (
        f"Purchased {quantity} shares of {ticker} for ${total_cost:.2f}. "
        f"New balance: ${logged_in_user.balance:.2f}"
    )