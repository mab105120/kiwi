from typing import Tuple
import app.cli.input_collector as collector
from app.domain.User import User
import app.database as db
from app.session_state import set_logged_in_user, reset_logged_in_user

class LoginError(Exception): pass

def login():
    user_inputs = collector.collect_inputs({
        "Username": "username",
        "Password": "password"
    })
    username = user_inputs["username"]
    password= user_inputs["password"]
    _login(username, password)

def _login(username, password):
    try:
        session = db.get_session()
        user = session.query(User).filter(User.username == username).first()
        if not user or str(user.password) != password:
            raise LoginError("Invalid username or password")
        set_logged_in_user(user)
    except Exception as e:
        session.rollback() if session else None
        raise LoginError(f"Login Failed: {str(e)}")
    finally:
        session.close() if session else None

def logout():
    reset_logged_in_user()