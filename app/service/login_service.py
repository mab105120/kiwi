from typing import Tuple
from rich.console import Console
import db

_console = Console()

def get_login_inputs() -> Tuple[str, str]:
    username = _console.input("Username: ")
    password=_console.input("Password: ")
    _console.print("\n")
    return username, password

def login():
    username, password = get_login_inputs()
    user = db.query_user(username)
    if not user or user.password != password:
        raise Exception("Login Failed")
    db.set_logged_in_user(user)