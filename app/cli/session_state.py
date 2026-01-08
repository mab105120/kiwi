from app.models import User

_logged_in_user: User | None = None


def get_logged_in_user() -> User | None:
    return _logged_in_user


def set_logged_in_user(user: User):
    global _logged_in_user  # anti-pattern but ok for this simple app
    _logged_in_user = user


def reset_logged_in_user():
    global _logged_in_user
    _logged_in_user = None
