from typing import List
from app.models import Security, Portfolio, Investment
from app.service import transaction_service
import app.database as db

class SecurityException(Exception): pass
class InsufficientFundsError(Exception): pass

def get_all_securities() -> List[Security]:
    session = None
    try:
        session = db.get_session()
        securities = session.query(Security).all()
        return securities
    except Exception as e:
        raise SecurityException(f"Failed to retrieve securities due to error: {str(e)}")
    finally:
        session.close() if session else None

def get_security_by_ticker(ticker: str) -> Security | None:
    session = None
    try:
        session = db.get_session()
        security = session.query(Security).filter_by(ticker=ticker).one_or_none()
        return security
    except Exception as e:
        raise SecurityException(f"Failed to retrieve security due to error: {str(e)}")
    finally:
        session.close() if session else None

def execute_purchase_order(portfolio_id: int, ticker: str, quantity: int):
    session = None
    try:
        if not portfolio_id or not ticker or not quantity or quantity <= 0:
            raise SecurityException(f"Invalid purchase order parameters [portfolio_id={portfolio_id}, ticker={ticker}, quantity={quantity}]")
        session = db.get_session()
        portfolio = session.query(Portfolio).filter_by(id=portfolio_id).one_or_none()
        if not portfolio:
            raise SecurityException(f"Portfolio with id {portfolio_id} does not exist.")
        user = portfolio.user if portfolio else None
        if not user:
            raise SecurityException(f"User associated with the portfolio ({portfolio_id}) does not exist.")
        
        security = session.query(Security).filter_by(ticker=ticker).one_or_none()
        if not security:
            raise SecurityException(f"Security with ticker {ticker} does not exist.")
        
        total_cost = security.price * quantity
        if user.balance < total_cost:
            raise InsufficientFundsError("Insufficient funds to complete the purchase.")

        existing_investment = next((inv for inv in portfolio.investments if inv.ticker == ticker), None)
        if existing_investment:
            existing_investment.quantity += quantity
        else:
            portfolio.investments.append(Investment(ticker=ticker, quantity=quantity, security=security))

        user.balance -= total_cost
        session.commit()
        transaction_service.record_transaction(portfolio_id=portfolio.id, ticker=ticker, quantity=quantity, price=security.price, transaction_type="BUY")
    except InsufficientFundsError as e:
        session.rollback() if session else None
        raise e
    except Exception as e:
        session.rollback() if session else None
        raise SecurityException(f"Failed to execute purchase order due to error: {str(e)}")
    finally:
        session.close() if session else None