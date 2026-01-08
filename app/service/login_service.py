from app.cli.session_state import reset_logged_in_user, set_logged_in_user
from app.db import db
from app.models.User import User


class LoginError(Exception):
    pass


def login(username, password):
    try:
        user = db.session.query(User).filter(User.username == username).first()
        if not user or str(user.password) != password:
            raise LoginError('Invalid username or password')
        set_logged_in_user(user)
    except Exception as e:
        db.session.rollback()
        raise LoginError(f'Login Failed: {str(e)}')


def logout():
    reset_logged_in_user()
