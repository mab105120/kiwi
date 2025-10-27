from typing import Tuple
from cli.input_collector import collect_inputs
from domain.User import User
from database import get_session
from session_state import set_logged_in_user, reset_logged_in_user

class LoginError(Exception): pass

def _get_login_inputs() -> Tuple[str, str]:
    user_inputs = collect_inputs({
        "Username": "username",
        "Password": "password"
    })
    username = user_inputs["username"]
    password= user_inputs["password"]
    return username, password

def login():
    username, password = _get_login_inputs()
    try:
        session = get_session()
        user = session.query(User).filter(User.username == username).first()
        if not user or str(user.password) != password:
            raise LoginError("Login Failed: Invalid username or password")
        set_logged_in_user(user)
    except Exception as e:
        session.rollback() if session else None
        raise LoginError(f"Login Failed: {str(e)}")
    finally:
        session.close() if session else None


def logout():
    reset_logged_in_user()