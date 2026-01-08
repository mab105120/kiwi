from app.models import Transaction, User, Portfolio, Security
from rich.table import Table
from typing import List
from rich.console import Console

_console = Console()


def print_users_table(users: List[User]):
    table = Table(title="Users")
    table.add_column("Username", justify="right", style="cyan", no_wrap=True)
    table.add_column("First Name", style="magenta")
    table.add_column("Last Name", style="magenta")
    table.add_column("Balance", justify="right", style="green")
    for user in users:
        table.add_row(
            user.username, user.firstname, user.lastname, f"${user.balance:.2f}"
        )
    _console.print(table)


def print_transactions_table(transactions: List[Transaction]):
    if len(transactions) == 0:
        _console.print("No transactions exist for this portfolio.")
        return
    table = Table(title="Transactions")
    table.add_column("Id")
    table.add_column("Ticker")
    table.add_column("Type")
    table.add_column("Quantity", justify="right")
    table.add_column("Price", justify="right", style="green")
    table.add_column("Date", style="cyan")
    for transaction in transactions:
        table.add_row(
            str(transaction.transaction_id),
            transaction.ticker,
            transaction.transaction_type,
            str(transaction.quantity),
            f"${transaction.price:.2f}",
            transaction.date_time.strftime("%Y-%m-%d %H:%M:%S"),
        )
    _console.print(table)


def print_portfolios_table(portfolios: List[Portfolio]):
    if len(portfolios) == 0:
        _console.print("No portfolios exist. Add new portfolios")
        return
    table = Table(title="Portfolios")
    table.add_column("Id")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Value", justify="right", style="green")
    for portfolio in portfolios:
        table.add_row(
            str(portfolio.id),
            portfolio.name,
            portfolio.description,
            f"${portfolio.get_portfolio_value():.2f}",
        )
    _console.print(table)


def print_portfolio_with_investments_table(portfolio: Portfolio):
    if len(portfolio.investments) == 0:
        _console.print(f"No investments exist in portfolio with id {portfolio.id}")
        return
    table = Table(
        title=f"Investments in Portfolio {portfolio.name} (ID: {portfolio.id})"
    )
    table.add_column("Ticker", style="cyan")
    table.add_column("Issuer")
    table.add_column("Quantity", justify="right")
    table.add_column("Price", justify="right", style="green")
    table.add_column("Total Value", justify="right", style="green")
    for investment in portfolio.investments:
        total_value = investment.quantity * investment.security.price
        table.add_row(
            investment.security.ticker,
            investment.security.issuer,
            str(investment.quantity),
            f"${investment.security.price:.2f}",
            f"${total_value:.2f}",
        )
    _console.print(table)


def print_securities_table(securities: List[Security]):
    table = Table(title="Securities")
    table.add_column("Ticker", style="cyan")
    table.add_column("Issuer")
    table.add_column("Price", justify="right", style="green")
    for security in securities:
        table.add_row(security.ticker, security.issuer, f"${security.price:.2f}")
    _console.print(table)
