from __future__ import annotations
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Float
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db import db

if TYPE_CHECKING:
    # imports that are used only for type checking to avoid circular dependencies
    from app.models import Investment, Transaction


class Security(db.Model):
    __tablename__ = "security"
    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    issuer: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)

    investments: Mapped[List["Investment"]] = relationship(
        "Investment", back_populates="security", lazy="selectin"
    )

    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="security", lazy="selectin"
    )

    # this is needed because PyLance cannot infer the constructor signature from SQLAlchemy's Mapped class
    if TYPE_CHECKING:

        def __init__(self, *, ticker: str, issuer: str, price: float) -> None: ...

    def __str__(self):
        return f"<Security: ticker={self.ticker}; issuer={self.issuer}; price={self.price}; #investments={len(self.investments)}>"

    def __to_dict__(self):
        return {
            "ticker": self.ticker,
            "issuer": self.issuer,
            "price": self.price,
        }
