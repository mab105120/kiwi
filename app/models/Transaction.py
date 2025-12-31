import datetime
from app.database import Base
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.models import User, Portfolio, Security

class Transaction(Base):
    __tablename__ = "transaction"
    transaction_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(30), ForeignKey("user.username"), nullable=False)
    portfolio_id: Mapped[int] = mapped_column(Integer, ForeignKey("portfolio.id"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(30), ForeignKey("security.ticker"), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    date_time: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped[User] = relationship("User", back_populates="transactions", foreign_keys=[username], lazy="selectin")
    portfolio: Mapped[Portfolio] = relationship("Portfolio", back_populates="transactions", foreign_keys=[portfolio_id], lazy="selectin")
    security: Mapped[Security] = relationship("Security", back_populates="transactions", foreign_keys=[ticker], lazy="selectin")

    def __str__(self):
        return (
            f"<Transaction: id={self.transaction_id}; user={self.username}; "
            f"portfolio_id={self.portfolio_id}; ticker={self.ticker}; "
            f"type={self.transaction_type}; quantity={self.quantity}; "
            f"price={self.price}; date_time={self.date_time}>"
        )