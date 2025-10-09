from typing import List
from rich.table import Table
from rich.console import Console
from domain.Security import Security
import db

_console = Console()

def get_all_securities() -> List[Security]:
    return db.get_all_securities()

def print_all_securities(securities: List[Security]):
    table = Table(title="Securities")
    table.add_column("Ticker")
    table.add_column("Issuer")
    table.add_column("Price")
    for security in securities:
        table.add_row(security.ticker, security.issuer, str(security.price))
    _console.print(table)