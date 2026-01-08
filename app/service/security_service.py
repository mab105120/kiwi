import datetime
from typing import List

from app.db import db
from app.models import Investment, Portfolio, Security, Transaction


class SecurityException(Exception):
    pass


class InsufficientFundsError(Exception):
    pass


def get_all_securities() -> List[Security]:
    try:
        securities = db.session.query(Security).all()
        return securities
    except Exception as e:
        db.session.rollback()
        raise SecurityException(f'Failed to retrieve securities due to error: {str(e)}')


def get_security_by_ticker(ticker: str) -> Security | None:
    try:
        security = db.session.query(Security).filter_by(ticker=ticker).one_or_none()
        return security
    except Exception as e:
        db.session.rollback()
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

        security = db.session.query(Security).filter_by(ticker=ticker).one_or_none()
        if not security:
            raise SecurityException(f'Security with ticker {ticker} does not exist.')

        total_cost = security.price * quantity
        if user.balance < total_cost:
            raise InsufficientFundsError('Insufficient funds to complete the purchase.')

        existing_investment = next((inv for inv in portfolio.investments if inv.ticker == ticker), None)
        if existing_investment:
            existing_investment.quantity += quantity
        else:
            portfolio.investments.append(Investment(ticker=ticker, quantity=quantity, security=security))

        user.balance -= total_cost
        db.session.add(
            Transaction(
                portfolio_id=portfolio.id,
                username=user.username,
                ticker=ticker,
                quantity=quantity,
                price=security.price,
                transaction_type='BUY',
                date_time=datetime.datetime.now(),
            )
        )
        db.session.flush()
    except InsufficientFundsError as e:
        db.session.rollback()
        raise e
    except Exception as e:
        db.session.rollback()
        raise SecurityException(f'Failed to execute purchase order due to error: {str(e)}')
