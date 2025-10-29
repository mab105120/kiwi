from app.domain.User import User
from app.service.login_service import login, _login, logout, LoginError
from app.session_state import get_logged_in_user

def create_user_fixture(db_session):
    user = User(username='user', password='userpass', firstname='User Firstname', lastname='User Lastname', balance=1000.00)
    db_session.add(user)
    db_session.commit()

def test_login_success(db_session):
    create_user_fixture(db_session)
    assert get_logged_in_user() is None
    try:
        _login('user', 'userpass')
        assert get_logged_in_user() is not None
    except LoginError:
        assert False, "Login should not fail"
    finally:
        logout()

def test_get_login_inputs(monkeypatch):
    def mock_collect_inputs(_):
        return {
            "username": "testuser",
            "password": "testpass"
        }
    monkeypatch.setattr('app.cli.input_collector.collect_inputs', mock_collect_inputs)
    monkeypatch.setattr('app.service.login_service._login', lambda _, __: None)
    login()


def test_login_invalid_username(db_session):
    create_user_fixture(db_session)
    try:
        _login('invalid_user', 'userpass')
    except LoginError as e:
        assert str(e) == "Login Failed: Invalid username or password"
    else:
        assert False, "Expected LoginError was not raised"
    finally:
        logout()

def test_logout(db_session):
    create_user_fixture(db_session)
    assert get_logged_in_user() is None
    try:
        _login('user', 'userpass')
        logged_in_user = get_logged_in_user()
        assert logged_in_user is not None
        assert logged_in_user.username == 'user'
        logout()
        assert get_logged_in_user() is None
    except LoginError:
        assert False, "Login should not fail"