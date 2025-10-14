from typing import List
from rich.table import Table
import db
from cli.input_collector import collect_inputs
from domain.Portfolio import Portfolio

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

def delete_portfolio(portfolio_id: int) -> str:
    # if the portfolio does not exist or the investments attribute is not an empty list, raise an exception
    portfolio = db.get_portfolio_by_id(portfolio_id)
    if not portfolio:
        raise UnsupportedPortfolioOperationError(f"Portfolio with id {portfolio_id} does not exist")
    if len(portfolio.investments) > 0:
        raise UnsupportedPortfolioOperationError(f"Portfolio with id {portfolio_id} is not empty. Please liquidate investments before deleting the portfolio")
    db.delete_portfolio_by_id(portfolio_id)
    return f"Deleted portfolio with id {portfolio_id}"
