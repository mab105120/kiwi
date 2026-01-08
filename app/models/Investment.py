from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import relationship, mapped_column, Mapped
from app.db import db

if TYPE_CHECKING:
    from app.models import Security, Portfolio


class Investment(db.Model):
    __tablename__ = "investment"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), ForeignKey("security.ticker"))
    portfolio_id: Mapped[int] = mapped_column(Integer, ForeignKey("portfolio.id"))

    security: Mapped["Security"] = relationship(
        "Security", foreign_keys=[ticker], back_populates="investments", lazy="selectin"
    )

    portfolio: Mapped["Portfolio"] = relationship(
        "Portfolio",
        foreign_keys=[portfolio_id],
        back_populates="investments",
        lazy="selectin",
    )

    # this is needed because PyLance cannot infer the constructor signature from SQLAlchemy's Mapped class
    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            quantity: int | None = None,
            ticker: str | None = None,
            security: Security | None = None,
        ) -> None: ...

    def __str__(self):
        return f"<Investment: id={self.id}; portfolio id={self.portfolio_id}; quantity={self.quantity}; portfolio={self.portfolio}>"
