from typing import Dict, List
from rich.console import Console
import app.service.transaction_service as transaction_service
import app.service.login_service as login_service
import app.service.user_service as user_service
import app.service.portfolio_service as portfolio_service
import app.service.security_service as security_service
from app.models import Transaction, Portfolio
import app.cli.session_state as session_state

_console = Console()


def _collect_inputs(variables: Dict[str, str]) -> Dict[str, str]:
    input_vals = {}
    for label, var in variables.items():
        val = _console.input(f"{label}: ")
        input_vals[var] = val
    _console.print("\n")
    return input_vals


## User Wrapper Functions
def create_user() -> str:
    try:
        user_inputs = _collect_inputs(
            {
                "Username": "username",
                "Password": "password",
                "First Name": "firstname",
                "Last Name": "lastname",
                "Balance": "balance",
            }
        )
        username = user_inputs["username"]
        password = user_inputs["password"]
        firstname = user_inputs["firstname"]
        lastname = user_inputs["lastname"]
        balance = float(user_inputs["balance"])

        user_service.create_user(username, password, firstname, lastname, balance)
        return f"User {username} created successfully."
    except ValueError:
        raise user_service.UnsupportedUserOperationError(
            "Invalid input. Please try again."
        )


def delete_user() -> str:
    username = _collect_inputs({"Username of user to delete": "username"})["username"]
    user_service.delete_user(username)
    return f"User {username} deleted successfully"


## Portfolio Wrapper Functions
def create_portfolio() -> str:
    user_inputs = _collect_inputs(
        {"Portfolio name": "name", "Portfolio description": "description"}
    )
    name = user_inputs["name"]
    description = user_inputs["description"]
    user = session_state.get_logged_in_user()
    if not user:
        raise Exception(
            "Unexpected state encountered when creating portfolio. No user logged in"
        )
    portfolio_service.create_portfolio(name, description, user)
    return f"Created new portfolio {name}"


def get_portfolio_by_id() -> Portfolio:
    try:
        portfolio_id = int(
            _collect_inputs({"Portfolio ID": "portfolio_id"})["portfolio_id"]
        )
        portfolio = portfolio_service.get_portfolio_by_id(portfolio_id)
        if not portfolio:
            raise portfolio_service.UnsupportedPortfolioOperationError(
                f"Portfolio with id {portfolio_id} does not exist"
            )
        return portfolio
    except ValueError:
        raise portfolio_service.UnsupportedPortfolioOperationError(
            "Invalid input. Please try again."
        )


def delete_portfolio() -> str:
    try:
        portfolio_id = int(
            _collect_inputs({"Portfolio ID": "portfolio_id"})["portfolio_id"]
        )
        portfolio_service.delete_portfolio(portfolio_id)
        return f"Deleted portfolio with id {portfolio_id}"
    except ValueError:
        raise portfolio_service.UnsupportedPortfolioOperationError(
            "Invalid input. Please try again."
        )


def liquidate_investment() -> str:
    try:
        user_inputs = _collect_inputs(
            {
                "Portfolio ID": "portfolio_id",
                "Ticker": "ticker",
                "Quantity": "quantity",
                "Sale price": "sale_price",
            }
        )
        portfolio_id = int(user_inputs["portfolio_id"])
        ticker = user_inputs["ticker"]
        quantity = int(user_inputs["quantity"])
        sale_price = float(user_inputs["sale_price"])
        user = session_state.get_logged_in_user()
        if user is None:
            raise user_service.UnsupportedUserOperationError(
                "No user is currently logged in"
            )
        portfolio_service.liquidate_investment(
            portfolio_id, ticker, quantity, sale_price
        )
        return f"Liquidated {quantity} shares of {ticker} from portfolio with id {portfolio_id}."
    except ValueError:
        raise portfolio_service.UnsupportedPortfolioOperationError(
            "Invalid input. Please try again."
        )


## Security Wrapper Functions
def place_purchase_order() -> str:
    user_inputs = _collect_inputs(
        {"Portfolio ID": "portfolio_id", "Ticker": "ticker", "Quantity": "quantity"}
    )
    try:
        portfolio_id = int(user_inputs["portfolio_id"])
        ticker = user_inputs["ticker"]
        quantity = int(user_inputs["quantity"])
        security_service.execute_purchase_order(portfolio_id, ticker, quantity)
        return f"Purchased {quantity} shares of {ticker}"
    except ValueError:
        raise security_service.SecurityException("Invalid input. Please try again.")


## Transaction Wrapper Functions
def get_transactions_by_user() -> List[Transaction]:
    user = session_state.get_logged_in_user()
    if user is None:
        raise user_service.UnsupportedUserOperationError(
            "No user is currently logged in"
        )
    username = user.username
    return transaction_service.get_transactions_by_user(username)


def get_transactions_by_portfolio_id() -> List[Transaction]:
    try:
        user_inputs = _collect_inputs({"Portfolio ID": "portfolio_id"})
        portfolio_id = int(user_inputs["portfolio_id"])
        return transaction_service.get_transactions_by_portfolio_id(portfolio_id)
    except ValueError:
        raise user_service.UnsupportedUserOperationError(
            "Invalid input. Please try again."
        )


def get_transactions_by_ticker() -> List[Transaction]:
    user_inputs = _collect_inputs({"Ticker": "ticker"})
    ticker = user_inputs["ticker"]
    return transaction_service.get_transactions_by_ticker(ticker)


def login():
    user_inputs = _collect_inputs({"Username": "username", "Password": "password"})
    username = user_inputs["username"]
    password = user_inputs["password"]
    login_service.login(username, password)
