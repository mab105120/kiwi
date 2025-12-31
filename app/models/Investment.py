from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import relationship, mapped_column, Mapped
from app.database import Base

if TYPE_CHECKING:
    from models.Portfolio import Portfolio
    from models.Security import Security

class Investment(Base):
    __tablename__ = 'investment'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), ForeignKey('security.ticker'))
    portfolio_id: Mapped[int] = mapped_column(Integer, ForeignKey('portfolio.id'))

    security: Mapped["Security"] = relationship(
        "Security",
        foreign_keys=[ticker],
        back_populates="investments",
        lazy="selectin")
    
    portfolio: Mapped["Portfolio"] = relationship(
        "Portfolio",
        foreign_keys=[portfolio_id],
        back_populates="investments",
        lazy="selectin")

    def __str__(self):
        return f"<Investment: id={self.id}; portfolio id={self.portfolio_id}; quantity={self.quantity}; portfolio={self.portfolio}>"