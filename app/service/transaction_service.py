from typing import List
from app.models import Transaction
import app.database as db

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