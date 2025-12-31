from __future__ import annotations
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Float
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database import Base

if TYPE_CHECKING:
    from app.models import Investment, Transaction

class Security(Base):
    __tablename__ = 'security'
    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    issuer: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)

    investments: Mapped[List["Investment"]] = relationship(
        "Investment",
        back_populates="security",
        lazy="selectin")

    transactions: Mapped[List["Transaction"]] = relationship(
    "Transaction",
    back_populates="security",
    lazy="selectin")

    def __str__(self):
        return f"<Security: ticker={self.ticker}; issuer={self.issuer}; price={self.price}; #investments={len(self.investments)}>"