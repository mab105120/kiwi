# native modules
import sys
from typing import Dict, Tuple, List
# external dependencies
from rich.console import Console
from rich.table import Table
# internal dependencies
from cli import constants
from domain.MenuFunctions import MenuFunctions
from service.login_service import login, logout
from service.user_service import get_all_users, create_user, delete_user, print_all_users
from service.security_service import get_all_securities, print_all_securities
from service.portfolio_service import get_all_portfolios, print_all_portfolios, create_portfolio
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

def navigate_to_manage_user_menu() -> int:
    logged_in_user = db.get_logged_in_user()
    if logged_in_user and logged_in_user.username != "admin":
        raise UnsupportedMenuError("Only admin user can manage users")
    return constants.MANAGE_USERS_MENU

_router: Dict[str, MenuFunctions] = {
    "0.1": MenuFunctions(executor=login, navigator=lambda: constants.MAIN_MENU),
    "1.1": MenuFunctions(navigator=navigate_to_manage_user_menu),
    "1.2": MenuFunctions(navigator=lambda: constants.MANAGE_PORTFOLIO),
    "1.3": MenuFunctions(navigator=lambda: constants.MARKET_PLACE),
    "2.1": MenuFunctions(executor=get_all_users, printer=lambda users: _console.print(print_all_users(users))),
    "2.2": MenuFunctions(executor=create_user, printer=lambda x: _console.print(f'\n{x}')),
    "2.3": MenuFunctions(executor=delete_user, printer=lambda x: _console.print(f'\n{x}')),
    "3.1": MenuFunctions(executor=get_all_portfolios, printer=lambda portfolios: _console.print(print_all_portfolios(portfolios))),
    "3.2": MenuFunctions(executor=create_portfolio, printer=lambda x: _console.print(f'\n{x}')),
    "4.1": MenuFunctions(executor=get_all_securities, printer=lambda securities: _console.print(print_all_securities(securities))),
}

def print_error(error: str):
    _console.print(error, style="red")

def handle_user_selection(menu_id: int, user_selection: int):
    if user_selection == 0:
        if menu_id == constants.LOGIN_MENU:
            sys.exit(0)
        elif menu_id == constants.MAIN_MENU:
            logout()
            print_menu(constants.LOGIN_MENU)
        else:
            print_menu(constants.MAIN_MENU)
    formatted_user_input = f"{str(menu_id)}.{str(user_selection)}"
    menu_functions = _router[formatted_user_input]
    try:
        if menu_functions.executor:
            result = menu_functions.executor()
            if result is not None and menu_functions.printer:
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
