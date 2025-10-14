
from typing import List
from rich.table import Table
from domain.User import User
from cli.input_collector import collect_inputs
import db

class UnsupportedUserOperationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)

def get_all_users() -> List[User]:
    return db.query_all_users()

def print_all_users(users: List[User]) -> Table:
    table = Table(title="Users")
    table.add_column("Username", justify="right", style="cyan", no_wrap=True)
    table.add_column("First Name", style="magenta")
    table.add_column("Last Name", style="magenta")
    table.add_column("Balance", justify="right", style="green")
    for user in users:
        table.add_row(user.username, user.firstname, user.lastname, f"${user.balance:.2f}")
    return table

def create_user() -> str:
    try:
        user_inputs = collect_inputs({
            "Username": "username",
            "Password": "password",
            "First Name": "firstname",
            "Last Name": "lastname",
            "Balance": "balance"
        })
        username = user_inputs["username"]
        password = user_inputs["password"]
        firstname = user_inputs["firstname"]
        lastname = user_inputs["lastname"]
        balance = float(user_inputs["balance"])
    except ValueError:
        raise UnsupportedUserOperationError("Invalid input. Please try again.")
    db.create_new_user(User(username, password, firstname, lastname, balance))
    return f"User {username} created successfully"

def delete_user() -> str:
    username = collect_inputs({"Username of user to delete": "username"})["username"]
    if username == "admin":
        raise UnsupportedUserOperationError("Cannot delete admin user")
    if not db.query_user(username):
        raise UnsupportedUserOperationError(f"User with username {username} does not exist")
    db.delete_user(username)
    return f"User {username} deleted successfully"