from typing import Tuple
from cli.input_collector import collect_inputs
import db

class LoginError(Exception):
    def __init__(self, message: str):
        super().__init__(message)

def get_login_inputs() -> Tuple[str, str]:
    user_inputs = collect_inputs({
        "Username": "username",
        "Password": "password"
    })
    username = user_inputs["username"]
    password= user_inputs["password"]
    return username, password

def login():
    username, password = get_login_inputs()
    user = db.query_user(username)
    if not user or user.password != password:
        raise LoginError("Login Failed: Invalid username or password")
    db.set_logged_in_user(user)

def logout():
    db.reset_logged_in_user()