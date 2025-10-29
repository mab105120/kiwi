# native modules
import sys
from typing import Dict
# external dependencies
from rich.console import Console
from rich.table import Table
# internal dependencies
from app.session_state import get_logged_in_user
from app.cli import constants
from app.domain.MenuFunctions import MenuFunctions
from app.service.login_service import login, logout
from app.service.user_service import get_all_users, create_user, delete_user, build_users_table
from app.service.security_service import get_all_securities, build_securities_table, place_purchase_order
from app.service.portfolio_service import get_all_portfolios, build_portfolios_table, create_portfolio, delete_portfolio, build_portfolio_investments_table, liquidate_investment

class UnsupportedMenuError(Exception): pass

_console = Console()
_menus: Dict[int, str] = {
    constants.LOGIN_MENU: "----\nWelcome to Kiwi\n----\n1. Login\n0. Exit",
    constants.MAIN_MENU: "----\nMain Menu\n----\n1. Manage Users\n2. Manage portfolios\n3. Market place\n0. Logout",
    constants.MANAGE_USERS_MENU: "----\nManage Users\n----\n1. View users\n2. Add user\n3. Delete user\n0. Back to main menu",
    constants.MANAGE_PORTFOLIO: "----\nPortfolio Menu\n----\n1. View portfolios\n2. Create new portfolio\n3. Delete Portfolio\n4. View Investments\n5. Liquidate investment\n0. Back to main menu",
    constants.MARKET_PLACE: "----\nMarketplace\n----\n1. View securities\n2. Place purchase order\n0. Back to main menu"
}

def navigate_to_manage_user_menu() -> int:
    logged_in_user = get_logged_in_user()
    if logged_in_user and logged_in_user.username != "admin":
        raise UnsupportedMenuError("Only admin user can manage users")
    return constants.MANAGE_USERS_MENU

_router: Dict[str, MenuFunctions] = {
    "0.1": MenuFunctions(executor=login, navigator=lambda: constants.MAIN_MENU),
    "1.1": MenuFunctions(navigator=navigate_to_manage_user_menu),
    "1.2": MenuFunctions(navigator=lambda: constants.MANAGE_PORTFOLIO),
    "1.3": MenuFunctions(navigator=lambda: constants.MARKET_PLACE),
    "2.1": MenuFunctions(executor=get_all_users, printer=lambda users: _console.print(build_users_table(users))),
    "2.2": MenuFunctions(executor=create_user, printer=lambda x: _console.print(f'\n{x}')),
    "2.3": MenuFunctions(executor=delete_user, printer=lambda x: _console.print(f'\n{x}')),
    "3.1": MenuFunctions(executor=get_all_portfolios, printer=lambda portfolios: _console.print(build_portfolios_table(portfolios))),
    "3.2": MenuFunctions(executor=create_portfolio, printer=lambda x: _console.print(f'\n{x}')),
    "3.3": MenuFunctions(executor=delete_portfolio, printer=lambda x: _console.print(f'\n{x}')),
    "3.4": MenuFunctions(executor=build_portfolio_investments_table, printer=lambda table: _console.print(table)),
    "3.5": MenuFunctions(executor=liquidate_investment, printer=lambda x: _console.print(f'\n{x}')),
    "4.1": MenuFunctions(executor=get_all_securities, printer=lambda securities: _console.print(build_securities_table(securities))),
    "4.2": MenuFunctions(executor=place_purchase_order, printer=lambda x: _console.print(f'\n{x}')),
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
    menu_functions = _router.get(formatted_user_input)
    if not menu_functions:
        print_error("Invalid menu selection. Please try again.")
        print_menu(menu_id)
        return
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
    try:
        _console.print(_menus[menu_id])
        user_selection = int(_console.input(">> ")) # TODO: check if the user input is valid
    except ValueError:
        print_error("Invalid input. Please try again.")
        print_menu(menu_id)
    except KeyError:
        print_error("Invalid menu selection. Please try again.")
        print_menu(menu_id)
    handle_user_selection(menu_id, user_selection)
