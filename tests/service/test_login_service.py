import pytest
from app.models import User
from app.service.login_service import login, logout, LoginError
from app.cli.session_state import get_logged_in_user


def create_user_fixture(db_session):
    user = User(
        username="user",
        password="userpass",
        firstname="User Firstname",
        lastname="User Lastname",
        balance=1000.00,
    )
    db_session.add(user)
    db_session.commit()


def test_login_success(db_session):
    create_user_fixture(db_session)
    assert get_logged_in_user() is None
    try:
        login("user", "userpass")
        assert get_logged_in_user() is not None
    except LoginError:
        assert False, "Login should not fail"
    finally:
        logout()


def test_login_invalid_username(db_session):
    create_user_fixture(db_session)
    with pytest.raises(LoginError):
        try:
            login("invalid_user", "userpass")
        finally:
            logout()


def test_logout(db_session):
    create_user_fixture(db_session)
    assert get_logged_in_user() is None
    try:
        login("user", "userpass")
        logged_in_user = get_logged_in_user()
        assert logged_in_user is not None
        assert logged_in_user.username == "user"
        logout()
        assert get_logged_in_user() is None
    except LoginError:
        assert False, "Login should not fail"
