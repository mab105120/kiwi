from typing import List
from rich.table import Table
import db
from cli.input_collector import collect_inputs
from domain.Portfolio import Portfolio
from domain.Investment import Investment

class UnsupportedPortfolioOperationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)

def create_portfolio() -> str:
    user_inputs = collect_inputs({
        "Portfolio name": "name", # TODO: remove the colon and space
        "Portfolio description": "description" 
    })
    name = user_inputs["name"]
    description = user_inputs["description"]
    user = db.get_logged_in_user()
    if not user:
        raise Exception("Unexpected state encountered when creating portfolio. No user logged in")
    portfolio = Portfolio(name, description, user)
    db.create_new_portfolio(portfolio)
    return f"Created new portfolio {name}"

def get_all_portfolios() -> List[Portfolio]:
    return db.get_all_portfolio_logged_in_user()

def print_all_portfolios(portfolios: List[Portfolio]) -> Table|str:
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

def create_investments_in_portfolio_table() -> Table:
    try:
        portfolio_id = int(collect_inputs({"Portfolio ID to view investments": "portfolio_id"})["portfolio_id"])
    except ValueError:
        raise UnsupportedPortfolioOperationError("Invalid input. Please try again.")
    portfolio = db.get_portfolio_by_id(portfolio_id)
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

def delete_portfolio() -> str:
    try:
        portfolio_id = int(collect_inputs({"Portfolio ID to delete": "portfolio_id"})["portfolio_id"])
    except ValueError:
        raise UnsupportedPortfolioOperationError("Invalid input. Please try again.")
    portfolio = db.get_portfolio_by_id(portfolio_id)
    if not portfolio:
        raise UnsupportedPortfolioOperationError(f"Portfolio with id {portfolio_id} does not exist")
    if len(portfolio.investments) > 0:
        raise UnsupportedPortfolioOperationError(f"Portfolio with id {portfolio_id} is not empty. Please liquidate investments before deleting the portfolio")
    db.delete_portfolio_by_id(portfolio_id)
    return f"Deleted portfolio with id {portfolio_id}"

def add_investment_to_portfolio(portfolio: Portfolio, investment: Investment):
    for existing_investment in portfolio.investments:
        if existing_investment.security.ticker == investment.security.ticker:
            existing_investment.quantity += investment.quantity
            return
    portfolio.investments.append(investment)

def liquidate_investment() -> str:
    try:
        user_inputs = collect_inputs({
            "Portfolio ID": "portfolio_id",
            "Ticker": "ticker",
            "Quantity": "quantity",
            "Sale price": "sale_price"
        })
        portfolio_id = int(user_inputs["portfolio_id"])
        ticker = user_inputs["ticker"]
        quantity = int(user_inputs["quantity"])
        sale_price = float(user_inputs["sale_price"])
    except ValueError:
        raise UnsupportedPortfolioOperationError("Invalid input. Please try again.")
    portfolio = db.get_portfolio_by_id(portfolio_id)
    if not portfolio:
        raise UnsupportedPortfolioOperationError(f"Portfolio with id {portfolio_id} does not exist")
    investment = next((inv for inv in portfolio.investments if inv.security.ticker == ticker), None)
    if not investment:
        raise UnsupportedPortfolioOperationError(f"No investment with ticker {ticker} exists in portfolio with id {portfolio_id}")
    if investment.quantity < quantity:
        raise UnsupportedPortfolioOperationError(f"Cannot liquidate {quantity} shares of {ticker}. Only {investment.quantity} shares available in portfolio")
    total_proceeds = sale_price * quantity
    logged_in_user = db.get_logged_in_user()
    if not logged_in_user:
        raise Exception("Unexpected state encountered when liquidating investment. No user logged in")
    logged_in_user.balance += total_proceeds
    investment.quantity -= quantity
    if investment.quantity == 0:
        portfolio.investments.remove(investment)
    return f"Liquidated {quantity} shares of {ticker} from portfolio with id {portfolio_id}. Added ${total_proceeds:.2f} to user balance"