from typing import List
from sqlalchemy.exc import IntegrityError
from app.models import User
import app.database as db

class UnsupportedUserOperationError(Exception): pass

def get_user_by_username(username: str) -> User | None:
    session = None
    try:
        if not username:
            raise UnsupportedUserOperationError("Username cannot be empty")
        session = db.get_session()
        return session.query(User).filter_by(username=username).one_or_none()
    except Exception as e:
        raise UnsupportedUserOperationError(f"Failed to retrieve user due to error: {str(e)}")
    finally:
        session.close() if session else None

def get_all_users() -> List[User]:
    session = None
    try:
        session = db.get_session()
        users = session.query(User).all()
        return users
    except Exception as e:
        raise UnsupportedUserOperationError(f"Failed to retrieve users due to error: {str(e)}")
    finally:
        session.close() if session else None

def update_user_balance(username: str, new_balance: float):
    session = None
    try:
        session = db.get_session()
        user = session.query(User).filter_by(username=username).one_or_none()
        if not user:
            raise UnsupportedUserOperationError(f"User with username {username} does not exist")
        user.balance = new_balance
        session.commit()
    except Exception as e:
        raise UnsupportedUserOperationError(f"Failed to update user balance due to error: {str(e)}")
    finally:
        session.close() if session else None

def create_user(username: str, password: str, firstname: str, lastname: str, balance: float):
    session = None
    try:
        session = db.get_session()
        session.add(User(username=username, password=password, firstname=firstname, lastname=lastname, balance=balance))
        session.commit()
    except Exception as e:
        raise UnsupportedUserOperationError(f"Failed to create user due to error: {str(e)}")
    finally:
        session.close() if session else None
    

def delete_user(username: str):
    if username == "admin":
        raise UnsupportedUserOperationError("Cannot delete admin user")
    if not username:
        raise UnsupportedUserOperationError("Username cannot be empty")
    session = None
    try:
        session = db.get_session()
        user = session.query(User).filter_by(username=username).one_or_none()
        if not user:
            raise UnsupportedUserOperationError(f"User with username {username} does not exist")
        session.delete(user)
        session.commit()
    except IntegrityError:
        session.rollback() if session else None
        raise UnsupportedUserOperationError(f"Cannot delete user {username} due to existing dependencies")
    except UnsupportedUserOperationError as e:
        raise e
    except Exception as e:
        raise UnsupportedUserOperationError(f"Failed to delete user due to error: {str(e)}")
    finally:
        session.close() if session else None