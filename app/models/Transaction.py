from typing import TYPE_CHECKING
import datetime
from app.db import db
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column

if TYPE_CHECKING:
    # imports that are used only for type checking to avoid circular dependencies
    from app.models import User, Portfolio, Security


class Transaction(db.Model):
    __tablename__ = "transaction"
    transaction_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    username: Mapped[str] = mapped_column(
        String(30), ForeignKey("user.username"), nullable=False
    )
    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolio.id"), nullable=False
    )
    ticker: Mapped[str] = mapped_column(
        String(30), ForeignKey("security.ticker"), nullable=False
    )
    transaction_type: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    date_time: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped["User"] = relationship(
        "User", back_populates="transactions", foreign_keys=[username], lazy="selectin"
    )
    portfolio: Mapped["Portfolio"] = relationship(
        "Portfolio",
        back_populates="transactions",
        foreign_keys=[portfolio_id],
        lazy="selectin",
    )
    security: Mapped["Security"] = relationship(
        "Security",
        back_populates="transactions",
        foreign_keys=[ticker],
        lazy="selectin",
    )

    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            username: str,
            portfolio_id: int,
            ticker: str,
            transaction_type: str,
            quantity: int,
            price: float,
            date_time: datetime.datetime,
        ) -> None: ...

    def __str__(self):
        return (
            f"<Transaction: id={self.transaction_id}; user={self.username}; "
            f"portfolio_id={self.portfolio_id}; ticker={self.ticker}; "
            f"type={self.transaction_type}; quantity={self.quantity}; "
            f"price={self.price}; date_time={self.date_time}>"
        )

    def __to_dict__(self):
        return {
            "transaction_id": self.transaction_id,
            "username": self.username,
            "portfolio_id": self.portfolio_id,
            "ticker": self.ticker,
            "transaction_type": self.transaction_type,
            "quantity": self.quantity,
            "price": self.price,
            "date_time": self.date_time.isoformat(),
        }
