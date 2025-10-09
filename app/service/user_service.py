
from typing import List
from rich.console import Console
from rich.table import Table
from domain.User import User
import db


_console = Console()

def get_all_users() -> List[User]:
    return db.query_all_users()

def print_all_users(users: List[User]):
    table = Table(title="Users")
    table.add_column("Username", justify="right", style="cyan", no_wrap=True)
    table.add_column("First Name", style="magenta")
    table.add_column("Last Name", style="magenta")
    table.add_column("Balance", justify="right", style="green")
    for user in users:
        table.add_row(user.username, user.firstname, user.lastname, f"${user.balance:.2f}")
    _console.print(table)

def create_user() -> str:
    username = _console.input("Username: ")
    password = _console.input("Password: ")
    firstname = _console.input("First Name: ")
    lastname = _console.input("Last Name: ")
    balance = float(_console.input("Balance: "))
    db.create_new_user(User(username, password, firstname, lastname, balance))
    return f"User {username} created successfully"

def delete_user() -> str:
    username = _console.input("Username of the user to delete: ")
    db.delete_user(username)
    return f"User {username} deleted successfully"