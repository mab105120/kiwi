import pytest
import app.service.user_service as user_service
from app.models import User
from app.service.portfolio_service import create_portfolio

def test_get_all_users_exception(db_session, monkeypatch):
    def raise_exception(_):
        raise Exception("Database error")
    monkeypatch.setattr(db_session, 'query', raise_exception)
    with pytest.raises(user_service.UnsupportedUserOperationError) as e:
        user_service.get_all_users()
    assert str(e.value) == "Failed to retrieve users due to error: Database error"

def test_create_user(db_session):
    users_before = user_service.get_all_users()
    initial_count = len(users_before)
    user_service.create_user('test_user75', 'xxx', 'Test', 'User', 100.00)
    users_after = user_service.get_all_users()
    assert len(users_after) == initial_count + 1
    tests_user = user_service.get_user_by_username('test_user75')
    assert tests_user is not None
    assert tests_user.firstname == 'Test'
    assert tests_user.lastname == 'User'
    assert tests_user.balance == 100.00

def test_create_user_db_exception(db_session, monkeypatch):
    def raise_exception(_):
        raise Exception("Database error")
    monkeypatch.setattr(db_session, 'add', raise_exception)
    with pytest.raises(user_service.UnsupportedUserOperationError) as e:
        user_service.create_user('test_user76', 'xxx', 'Test', 'User', 100.00)
    assert str(e.value) == "Failed to create user due to error: Database error"

def test_create_user_duplicate_username_raises(db_session):
    with pytest.raises(user_service.UnsupportedUserOperationError) as e:
        user_service.create_user('admin', 'xxx', 'Admin', 'User', 100.00)
    assert "Failed to create user due to error" in str(e.value)

def test_delete_user(db_session):
    users = user_service.get_all_users()
    initial_count = len(users)
    user_service.create_user('test_user77', 'xxx', 'Test', 'User', 150.00)
    users = user_service.get_all_users()
    assert len(users) == initial_count + 1
    user_service.delete_user('test_user77')
    users = user_service.get_all_users()
    assert len(users) == initial_count

def test_delete_user_db_exception(db_session, monkeypatch):
    user_service.create_user('test_user78', 'xxx', 'Test', 'User', 150.00)
    def raise_exception(_):
        raise Exception("Database error")
    monkeypatch.setattr(db_session, 'delete', raise_exception)
    with pytest.raises(user_service.UnsupportedUserOperationError) as e:
        user_service.delete_user('test_user78')
    assert str(e.value) == "Failed to delete user due to error: Database error"

def test_delete_admin_user_raises(db_session):
    with pytest.raises(user_service.UnsupportedUserOperationError) as e:
        user_service.delete_user('admin')
    assert str(e.value) == "Cannot delete admin user"

def test_delete_nonexistent_user_raises(db_session):
    with pytest.raises(user_service.UnsupportedUserOperationError) as e:
        user_service.delete_user('nonexistent_user')
    assert str(e.value) == "User with username nonexistent_user does not exist"

def test_delete_user_with_dependencies_raises(db_session):
    user_service.create_user('user1', 'xxx', 'Mr. User', 'Resu', 200.00)
    user1 = db_session.query(User).filter_by(username='user1').one()
    assert user1 is not None
    create_portfolio('Test Portfolio', 'Test Portfolio', user1)
    user1 = db_session.query(User).filter_by(username='user1').one()
    assert user1.portfolios is not None
    assert len(user1.portfolios) == 1
    with pytest.raises(user_service.UnsupportedUserOperationError) as e:
        user_service.delete_user('user1')
    assert "due to existing dependencies" in str(e.value)

def test_update_user_balance(db_session):
    admin = user_service.get_user_by_username('admin')
    assert admin is not None
    assert admin.balance == 1000.00
    user_service.update_user_balance('admin', 500.00)
    user = db_session.query(User).filter_by(username='admin').one()
    assert user.balance == 500.00

def test_update_nonexistent_user_balance_raises(db_session):
    with pytest.raises(user_service.UnsupportedUserOperationError) as e:
        user_service.update_user_balance('nonexistent_user', 300.00)
    assert "User with username nonexistent_user does not exist" in str(e.value)