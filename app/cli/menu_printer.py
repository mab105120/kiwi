# native modules
import sys
from typing import Dict, Tuple, List
# external dependencies
from rich.console import Console
from rich.table import Table
# internal dependencies
from cli import constants
from domain.MenuFunctions import MenuFunctions
from domain.User import User
from domain.Security import Security
from domain.Portfolio import Portfolio
import db

class UnsupportedMenuError(Exception):
    def __init__(self, message: str):
        super().__init__(message)

_console = Console()
_menus: Dict[int, str] = {
    constants.LOGIN_MENU: "----\nWelcome to Kiwi\n----\n1. Login\n0. Exit",
    constants.MAIN_MENU: "----\nMain Menu\n----\n1. Manage Users\n2. Manage portfolios\n3. Market place\n0. Logout",
    constants.MANAGE_USERS_MENU: "----\nManage Users\n----\n1. View users\n2. Add user\n3. Delete user\n0. Back to main menu",
    constants.MANAGE_PORTFOLIO: "----\nPortfolio Menu\n----\n1. View portfolios\n2. Create new portfolio\n3. Liquidate investment\n0. Back to main menu",
    constants.MARKET_PLACE: "----\nMarketplace\n----\n1. View securities\n2. Place purchase order\n0. Back to main menu"
}

def get_login_inputs() -> Tuple[str, str]:
    username = _console.input("Username: ")
    password=_console.input("Password: ")
    _console.print("\n")
    return username, password

# throw an error if login failed, return nothing otherwise
def login():
    username, password = get_login_inputs()
    user = db.query_user(username)
    if not user or user.password != password:
        raise Exception("Login Failed")
    db.set_logged_in_user(user)
    
def get_all_users() -> List[User]:
    return db.query_all_users()

def print_all_users(users: List[User]):
    table = Table(title="Users")
    table.add_column("Username", justify="right", style="cyan", no_wrap=True)
    table.add_column("First Name", style="magenta")
    table.add_column("Last Name", style="magenta")
    table.add_column("Balance", justify="right", style="green")
    for user in users:
        table.add_row(user.username, user.firstname, user.lastname, f"${user.balance:.2f}")
    _console.print(table)

def create_user() -> str:
    username = _console.input("Username: ")
    password = _console.input("Password: ")
    firstname = _console.input("First Name: ")
    lastname = _console.input("Last Name: ")
    balance = float(_console.input("Balance: "))
    db.create_new_user(User(username, password, firstname, lastname, balance))
    return f"User {username} created successfully"

def delete_user() -> str:
    username = _console.input("Username of the user to delete: ")
    db.delete_user(username)
    return f"User {username} deleted successfully"

def navigate_to_manage_user_menu() -> int:
    logged_in_user = db.get_logged_in_user()
    if logged_in_user and logged_in_user.username != "admin":
        raise UnsupportedMenuError("Only admin user can manage users")
    return constants.MANAGE_USERS_MENU

def create_portfolio():
    name = _console.input("Portfolio name: ")
    description = _console.input("Portfolio description: ")
    investment_strategy = _console.input("Investment Strategy: ")
    user = db.get_logged_in_user()
    portfolio = Portfolio(name, description, investment_strategy, user)
    db.create_new_portfolio(portfolio)
    return f"Created new portfolio {name}"

def get_all_portfolios() -> List[Portfolio]:
    return db.get_all_portfolio_logged_in_user()

def print_all_portfolios(portfolios: List[Portfolio]):
    if len(portfolios) == 0:
        _console.print("No portfolios exist. Add new portfolios")
    table = Table(title="Portfolios")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Investment strategy")
    table.add_column("Username")
    for portfolio in portfolios:
        table.add_row(portfolio.name, portfolio.description, portfolio.investment_strategy, portfolio.user.username)
    _console.print(table)
    

def get_all_securities() -> List[Security]:
    return db.get_all_securities()

def print_all_securities(securities: List[Security]):
    table = Table(title="Securities")
    table.add_column("Ticker")
    table.add_column("Issuer")
    table.add_column("Price")
    for security in securities:
        table.add_row(security.ticker, security.issuer, str(security.price))
    _console.print(table)

_router: Dict[str, MenuFunctions] = {
    "0.1": MenuFunctions(executor=login, navigator=lambda: constants.MAIN_MENU),
    "1.1": MenuFunctions(navigator=navigate_to_manage_user_menu),
    "1.2": MenuFunctions(navigator=lambda: constants.MANAGE_PORTFOLIO),
    "2.1": MenuFunctions(executor=get_all_users, printer=print_all_users),
    "2.2": MenuFunctions(executor=create_user, printer=lambda x: _console.print(f'\n{x}')), # add user
    "2.3": MenuFunctions(executor=delete_user, printer=lambda x: _console.print(f'\n{x}')), # delete user
    "1.3": MenuFunctions(navigator=lambda: constants.MARKET_PLACE),
    "4.1": MenuFunctions(executor=get_all_securities, printer=print_all_securities),
    "3.1": MenuFunctions(executor=get_all_portfolios, printer=print_all_portfolios),
    "3.2": MenuFunctions(executor=create_portfolio, printer=lambda x: _console.print(f'\n{x}'))
}

def print_error(error: str):
    _console.print(error, style="red")

def handle_user_selection(menu_id: int, user_selection: int):
    if user_selection == 0:
        if menu_id == constants.LOGIN_MENU:
            sys.exit(0)
        elif menu_id == constants.MAIN_MENU:
            db.reset_logged_in_user()
            print_menu(constants.LOGIN_MENU)
        else:
            print_menu(constants.MAIN_MENU)
    formatted_user_input = f"{str(menu_id)}.{str(user_selection)}"
    menu_functions = _router[formatted_user_input]
    try:
        if menu_functions.executor:
            result = menu_functions.executor()
            if result and menu_functions.printer:
                menu_functions.printer(result)
        if menu_functions.navigator:
            print_menu(menu_functions.navigator())
        else: 
            print_menu(menu_id)
    except Exception as e:
        print_error(f"Error: {str(e)}")
        print_menu(menu_id)


def print_menu(menu_id: int):
    _console.print(_menus[menu_id])
    user_selection = int(_console.input(">> ")) # TODO: check if the user input is valid
    handle_user_selection(menu_id, user_selection)
