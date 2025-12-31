from typing import List
import datetime
from app.models import Transaction, Portfolio, Security
import app.database as db

class TransactionOperationError(Exception): pass

def record_transaction(portfolio_id: int, ticker: str, quantity: int, price: float, transaction_type: str) -> int:
    session = None
    try:
        if portfolio_id is None or not ticker or quantity <= 0 or price <= 0.0 or transaction_type not in ['BUY', 'SELL']:
            raise TransactionOperationError(f"Invalid transaction parameters [portfolio_id={portfolio_id}, ticker={ticker}, quantity={quantity}, price_per_unit={price}, transaction_type={transaction_type}]")
        session = db.get_session()
        portfolio = session.query(Portfolio).filter_by(id=portfolio_id).one_or_none()
        if not portfolio:
            raise TransactionOperationError(f"Portfolio with id {portfolio_id} does not exist")
        user = portfolio.user
        if not user:
            raise TransactionOperationError(f"User associated with portfolio id {portfolio_id} does not exist")
        username = user.username
        security = session.query(Security).filter_by(ticker=ticker).one_or_none()
        if not security:
            raise TransactionOperationError(f"Security with ticker {ticker} does not exist")
        transaction = Transaction(
            portfolio_id=portfolio_id,
            username=username,
            ticker=ticker,
            quantity=quantity,
            price=price,
            transaction_type=transaction_type,
            date_time=datetime.datetime.now()
        )
        session.add(transaction)
        session.commit()
        return transaction.transaction_id
    except Exception as e:
        session.rollback() if session else None
        raise TransactionOperationError(f"Failed to record transaction due to error: {str(e)}")
    finally:
        session.close() if session else None

def get_transactions_by_user(username: str) -> List[Transaction]:
    session = None
    try:
        session = db.get_session()
        transactions = session.query(Transaction).filter(Transaction.username == username).all()
        return transactions
    finally:
        if session:
            session.close()

def get_transactions_by_portfolio_id(portfolio_id: int) -> List[Transaction]:
    session = None
    try:
        session = db.get_session()
        transactions = session.query(Transaction).filter(Transaction.portfolio_id == portfolio_id).all()
        return transactions
    finally:
        if session:
            session.close()

def get_transactions_by_ticker(ticker: str) -> List[Transaction]:
    session = None
    try:
        session = db.get_session()
        transactions = session.query(Transaction).filter(Transaction.ticker == ticker).all()
        return transactions
    finally:
        if session:
            session.close()