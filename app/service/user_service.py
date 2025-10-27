from typing import List
from rich.table import Table
from sqlalchemy.exc import IntegrityError
from domain import User
from cli.input_collector import collect_inputs
import database

class UnsupportedUserOperationError(Exception): pass

def get_all_users() -> List[User]:
    try:
        session = database.get_session()
        users = session.query(User).all()
        return users
    except Exception as e:
        raise UnsupportedUserOperationError(f"Failed to retrieve users due to error: {str(e)}")
    finally:
        session.close() if session else None

def build_users_table(users: List[User]) -> Table:
    table = Table(title="Users")
    table.add_column("Username", justify="right", style="cyan", no_wrap=True)
    table.add_column("First Name", style="magenta")
    table.add_column("Last Name", style="magenta")
    table.add_column("Balance", justify="right", style="green")
    for user in users:
        table.add_row(user.username, user.firstname, user.lastname, f"${user.balance:.2f}")
    return table

def update_user_balance(username: str, new_balance: float) -> str:
    try:
        session = database.get_session()
        user = session.query(User).filter_by(username=username).one_or_none()
        if not user:
            raise UnsupportedUserOperationError(f"User with username {username} does not exist")
        user.balance = new_balance
        session.commit()
        return f"Updated balance for user {username} to ${new_balance:.2f}"
    except Exception as e:
        raise UnsupportedUserOperationError(f"Failed to update user balance due to error: {str(e)}")
    finally:
        session.close() if session else None

def create_user() -> str:
    try:
        user_inputs = collect_inputs({
            "Username": "username",
            "Password": "password",
            "First Name": "firstname",
            "Last Name": "lastname",
            "Balance": "balance"
        })
        username = user_inputs["username"]
        password = user_inputs["password"]
        firstname = user_inputs["firstname"]
        lastname = user_inputs["lastname"]
        balance = float(user_inputs["balance"])

        session = database.get_session()
        session.add(User(username=username, password=password, firstname=firstname, lastname=lastname, balance=balance))
        session.commit()
        return f"User {username} created successfully"
    except ValueError:
        raise UnsupportedUserOperationError("Invalid input. Please try again.")
    except Exception as e:
        raise UnsupportedUserOperationError(f"Failed to create user due to error: {str(e)}")
    finally:
        session.close() if session else None
    

def delete_user() -> str:
    try:
        username = collect_inputs({"Username of user to delete": "username"})["username"]
        if username == "admin":
            raise UnsupportedUserOperationError("Cannot delete admin user")
        session = database.get_session()
        user = session.query(User).filter_by(username=username).one_or_none()
        if not user:
            raise UnsupportedUserOperationError(f"User with username {username} does not exist")
        session.delete(user)
        session.commit()
        return f"User {username} deleted successfully"
    except UnsupportedUserOperationError as e:
        raise e
    except IntegrityError:
        session.rollback()
        raise UnsupportedUserOperationError(f"Cannot delete user {username} due to existing dependencies")
    except Exception as e:
        raise UnsupportedUserOperationError(f"Failed to delete user due to error: {str(e)}")
    finally:
        session.close() if session else None