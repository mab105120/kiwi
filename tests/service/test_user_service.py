from app.service.user_service import _create_user, create_user, build_users_table, get_all_users
from app.domain import User
from app.service.user_service import _delete_user, delete_user, UnsupportedUserOperationError, update_user_balance
from app.service.portfolio_service import _create_portfolio

def test_get_all_users_exception(db_session, monkeypatch):
    def raise_exception(_):
        raise Exception("Database error")
    monkeypatch.setattr(db_session, 'query', raise_exception)
    try:
        get_all_users()
    except UnsupportedUserOperationError as e:
        assert str(e) == "Failed to retrieve users due to error: Database error"
    else:
        assert False, "Expected UnsupportedUserOperationError was not raised"

def test_build_users_table(db_session):
    users = get_all_users()
    assert len(users) >= 1
    table = build_users_table(users)
    assert table is not None
    assert len(table.rows) == len(users)
    assert table.columns[0]._cells[0] == 'admin'

def test_create_user(db_session):
    _create_user('test_user75', 'xxx', 'Test', 'User', 100.00)
    users = get_all_users()
    assert len(users) == 2

def test_create_user_db_exception(db_session, monkeypatch):
    def raise_exception(_):
        raise Exception("Database error")
    monkeypatch.setattr(db_session, 'add', raise_exception)
    try:
        _create_user('test_user76', 'xxx', 'Test', 'User', 100.00)
    except UnsupportedUserOperationError as e:
        assert str(e) == "Failed to create user due to error: Database error"
    else:
        assert False, "Expected UnsupportedUserOperationError was not raised"

def test_create_user_duplicate_username_raises(db_session):
    try:
        _create_user('admin', 'xxx', 'Admin', 'User', 100.00)
    except UnsupportedUserOperationError as e:
        assert "Failed to create user due to error" in str(e)
    else:
        assert False, "Expected UnsupportedUserOperationError was not raised"

def test_create_user_inputs(monkeypatch):
    monkeypatch.setattr('app.cli.input_collector.collect_inputs', lambda _: {
        "username": "testuser",
        "password": "testpass",
        "firstname": "Test",
        "lastname": "User",
        "balance": "250.00"
    })
    monkeypatch.setattr('app.service.user_service._create_user', lambda u, p, f, l, b: f"User {u} created successfully")
    result = create_user()
    assert result == "User testuser created successfully"

def test_create_user_invalid_input_raises(monkeypatch):
    monkeypatch.setattr('app.cli.input_collector.collect_inputs', lambda _: {
        "username": "testuser",
        "password": "testpass",
        "firstname": "Test",
        "lastname": "User",
        "balance": "invalid_number"
    })
    try:
        create_user()
    except UnsupportedUserOperationError as e:
        assert str(e) == "Invalid input. Please try again."
    else:
        assert False, "Expected UnsupportedUserOperationError was not raised"

def test_delete_user_inputs(db_session, monkeypatch):
    monkeypatch.setattr('app.cli.input_collector.collect_inputs', lambda _: {"username": "testuser"})
    monkeypatch.setattr('app.service.user_service._delete_user', lambda username: f"User {username} deleted successfully")
    result = delete_user()
    assert result == "User testuser deleted successfully"

def test_delete_user(db_session):
    _create_user('test_user77', 'xxx', 'Test', 'User', 150.00)
    result = _delete_user('test_user77')
    assert result == "User test_user77 deleted successfully"
    users = get_all_users()
    assert len(users) == 1

def test_delete_user_db_exception(db_session, monkeypatch):
    _create_user('test_user78', 'xxx', 'Test', 'User', 150.00)
    def raise_exception(_):
        raise Exception("Database error")
    monkeypatch.setattr(db_session, 'delete', raise_exception)
    try:
        _delete_user('test_user78')
    except UnsupportedUserOperationError as e:
        assert str(e) == "Failed to delete user due to error: Database error"
    else:
        assert False, "Expected UnsupportedUserOperationError was not raised"

def test_delete_admin_user_raises(db_session):
    try:
        _delete_user('admin')
    except UnsupportedUserOperationError as e:
        assert str(e) == "Cannot delete admin user"
    else:
        assert False, "Expected UnsupportedUserOperationError was not raised"

def test_delete_nonexistent_user_raises(db_session):
    try:
        _delete_user('nonexistent_user')
    except UnsupportedUserOperationError as e:
        assert str(e) == "User with username nonexistent_user does not exist"
    else:
        assert False, "Expected UnsupportedUserOperationError was not raised"

def test_delete_user_with_dependencies_raises(db_session):
    _create_user('user1', 'xxx', 'Mr. User', 'Resu', 200.00)
    user1 = db_session.query(User).filter_by(username='user1').one()
    assert user1 is not None
    _create_portfolio('Test Portfolio', 'Test Portfolio', user1)
    user1 = db_session.query(User).filter_by(username='user1').one()
    assert user1.portfolios is not None
    assert len(user1.portfolios) == 1
    try:
        _delete_user('user1')
    except UnsupportedUserOperationError as e:
        assert "due to existing dependencies" in str(e)
    else:
        assert False, "Expected UnsupportedUserOperationError was not raised"

def test_update_user_balance(db_session):
    update_user_balance('admin', 500.00)
    user = db_session.query(User).filter_by(username='admin').one()
    assert user.balance == 500.00

def test_update_nonexistent_user_balance_raises(db_session):
    try:
        update_user_balance('nonexistent_user', 300.00)
    except UnsupportedUserOperationError as e:
        assert "User with username nonexistent_user does not exist" in str(e)
    else:
        assert False, "Expected UnsupportedUserOperationError was not raised"