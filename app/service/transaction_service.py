from typing import List

from app.db import db
from app.models import Transaction


def get_transactions_by_user(username: str) -> List[Transaction]:
    try:
        transactions = db.session.query(Transaction).filter(Transaction.username == username).all()
        return transactions
    except Exception as e:
        db.session.rollback()
        raise e


def get_transactions_by_portfolio_id(portfolio_id: int) -> List[Transaction]:
    try:
        transactions = db.session.query(Transaction).filter(Transaction.portfolio_id == portfolio_id).all()
        return transactions
    except Exception as e:
        db.session.rollback()
        raise e


def get_transactions_by_ticker(ticker: str) -> List[Transaction]:
    try:
        transactions = db.session.query(Transaction).filter(Transaction.ticker == ticker).all()
        return transactions
    except Exception as e:
        db.session.rollback()
        raise e
