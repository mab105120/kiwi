from typing import List
from rich.table import Table
from domain.Security import Security
import db

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