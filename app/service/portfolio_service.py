from typing import List
from rich.console import Console
from rich.table import Table
import db
from domain.Portfolio import Portfolio


_console = Console()

def create_portfolio():
    name = _console.input("Portfolio name: ")
    description = _console.input("Portfolio description: ")
    investment_strategy = _console.input("Investment Strategy: ")
    user = db.get_logged_in_user()
    portfolio = Portfolio(name, description, investment_strategy, user)
    db.create_new_portfolio(portfolio)
    return f"Created new portfolio {name}"

def get_all_portfolios() -> List[Portfolio]:
    return db.get_all_portfolio_logged_in_user()

def print_all_portfolios(portfolios: List[Portfolio]):
    if len(portfolios) == 0:
        _console.print("No portfolios exist. Add new portfolios")
    table = Table(title="Portfolios")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Investment strategy")
    table.add_column("Username")
    for portfolio in portfolios:
        table.add_row(portfolio.name, portfolio.description, portfolio.investment_strategy, portfolio.user.username)
    _console.print(table)
    