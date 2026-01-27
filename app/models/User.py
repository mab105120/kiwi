from __future__ import annotations

from typing import TYPE_CHECKING, List

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import db

if TYPE_CHECKING:
    # imports that are used only for type checking to avoid circular dependencies
    from app.models import Portfolio, PortfolioPermission, Transaction


class User(db.Model):
    __tablename__ = 'user'

    username: Mapped[str] = mapped_column(String(30), primary_key=True)
    firstname: Mapped[str] = mapped_column(String(30), nullable=False)
    lastname: Mapped[str] = mapped_column(String(30), nullable=False)
    balance: Mapped[float] = mapped_column(Float, nullable=False)

    portfolios: Mapped[List['Portfolio']] = relationship('Portfolio', back_populates='user', lazy='selectin')
    transactions: Mapped[List['Transaction']] = relationship('Transaction', back_populates='user', lazy='selectin')
    portfolio_permissions: Mapped[List['PortfolioPermission']] = relationship(
        'PortfolioPermission', back_populates='user', lazy='selectin', cascade='all, delete-orphan'
    )

    # this is needed because PyLance cannot infer the constructor signature from SQLAlchemy's Mapped class
    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            username: str,
            firstname: str,
            lastname: str,
            balance: float,
        ) -> None: ...

    def __str__(self):
        return (
            f"<User: username='{self.username}'; "
            f"name='{self.firstname} {self.lastname}'; "
            f'#portfolios={len(self.portfolios)}; '
            f'balance={self.balance})'
        )

    def __to_dict__(self):
        return {
            'username': self.username,
            'firstname': self.firstname,
            'lastname': self.lastname,
            'balance': self.balance,
        }
