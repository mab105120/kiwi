from domain.User import User
from domain.Security import Security
from domain.Portfolio import Portfolio
from typing import Dict, List

class UniqueConstraintError(Exception):
    def __init__(self, message: str):
        super().__init__(message)

_portfolio_id: int = 0

_users: Dict[str, User] = {
    "admin": User("admin", "adminpass", "Admin", "Admin", 0.0)
}

_securities: Dict[str, Security] = {
    "AAPL": Security("APPL", "Apple Inc", 100.00),
    "FB": Security("FB", "Meta Inc", 112),
    "MFST": Security("MSFT", "Microsoft Inc", 80)
}

_portfolios: Dict[int, Portfolio] = {}

_logged_in_user: User|None = None

def get_logged_in_user() -> User|None:
    return _logged_in_user

def set_logged_in_user(user: User):
    global _logged_in_user # anti-pattern but ok for this simple app
    _logged_in_user = user

def reset_logged_in_user():
    global _logged_in_user
    _logged_in_user = None

def query_user(username: str) -> User | None:
    return _users.get(username)

def query_all_users() -> List[User]:
    return list(_users.values())

def create_new_user(user: User):
    if user.username in _users:
        raise UniqueConstraintError(f"User with username {user.username} already exists")
    _users[user.username] = user

def delete_user(username: str):
    _users.pop(username, None)

def get_all_securities() -> List[Security]:
    return list(_securities.values())

def get_all_portfolios() -> List[Portfolio]:
    return list(_portfolios.values())

def get_all_portfolio_logged_in_user() -> List[Portfolio]:
    user_portfolios = []
    for portfolio in get_all_portfolios():
        if _logged_in_user and portfolio.user.username == _logged_in_user.username:
            user_portfolios.append(portfolio)
    return user_portfolios

def create_new_portfolio(portfolio: Portfolio) -> int:
    id = _portfolio_id
    portfolio.set_id(id)
    _portfolios[id] = portfolio
    increment_portfolio_id()
    return id

def increment_portfolio_id():
    global _portfolio_id
    _portfolio_id = _portfolio_id + 1