import datetime

from app.db import db
from app.models import Investment, Portfolio, Transaction
from app.service import alpha_vantage_client
from app.service.alpha_vantage_client import AlphaVantageError


class SecurityException(Exception):
    pass


class InsufficientFundsError(Exception):
    pass


def get_security_by_ticker(ticker: str):
    try:
        security_quote = alpha_vantage_client.get_quote(ticker)
        return security_quote
    except AlphaVantageError as e:
        raise SecurityException(f'Failed to retrieve security due to error: {str(e)}')
    except Exception as e:
        raise SecurityException(f'Failed to retrieve security due to error: {str(e)}')


def execute_purchase_order(portfolio_id: int, ticker: str, quantity: int):
    try:
        if portfolio_id is None or not ticker or not quantity or quantity <= 0:
            raise SecurityException(
                f'Invalid purchase order parameters [portfolio_id={portfolio_id}, ticker={ticker}, quantity={quantity}]'
            )
        portfolio = db.session.query(Portfolio).filter_by(id=portfolio_id).one_or_none()
        if not portfolio:
            raise SecurityException(f'Portfolio with id {portfolio_id} does not exist.')
        user = portfolio.user
        if not user:
            raise SecurityException(f'User associated with the portfolio ({portfolio_id}) does not exist.')

        # Fetch security details from Alpha Vantage API
        security_quote = alpha_vantage_client.get_quote(ticker)
        if not security_quote:
            raise SecurityException(f'Security with ticker {ticker} does not exist or market data unavailable.')

        total_cost = security_quote.price * quantity
        if user.balance < total_cost:
            raise InsufficientFundsError('Insufficient funds to complete the purchase.')

        existing_investment = next((inv for inv in portfolio.investments if inv.ticker == ticker), None)
        if existing_investment:
            existing_investment.quantity += quantity
        else:
            portfolio.investments.append(Investment(ticker=ticker, quantity=quantity))

        user.balance -= total_cost
        db.session.add(
            Transaction(
                portfolio_id=portfolio.id,
                username=user.username,
                ticker=ticker,
                quantity=quantity,
                price=security_quote.price,
                transaction_type='BUY',
                date_time=datetime.datetime.now(),
            )
        )
        db.session.flush()
    except Exception as e:
        db.session.rollback()
        raise SecurityException(f'Failed to execute purchase order: {str(e)}')
