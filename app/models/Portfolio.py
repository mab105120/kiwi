from __future__ import annotations
from typing import List, TYPE_CHECKING
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import relationship, mapped_column, Mapped
from app.db import db

if TYPE_CHECKING:
    # imports that are used only for type checking to avoid circular dependencies
    from app.models import Investment, User, Transaction


class Portfolio(db.Model):
    __tablename__ = "portfolio"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    owner: Mapped[str] = mapped_column(
        String(30), ForeignKey("user.username"), nullable=False
    )

    investments: Mapped[List["Investment"]] = relationship(
        "Investment", back_populates="portfolio", lazy="selectin"
    )

    user: Mapped["User"] = relationship(
        "User", foreign_keys=[owner], back_populates="portfolios", lazy="selectin"
    )

    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="portfolio", lazy="selectin"
    )

    # this is needed because PyLance cannot infer the constructor signature from SQLAlchemy's Mapped class
    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            name: str | None = None,
            user: User | None = None,
            description: str | None = None,
            id: int | None = None,
        ) -> None: ...

    def __str__(self):
        user_str = getattr(self, "user", None)
        username = user_str.username if user_str else "N/A"
        return f"<Portfolio: id={self.id}; name={self.name}; description={self.description}; user={username}; #investments={len(self.investments)}>"

    def get_portfolio_value(self) -> float:
        total_value = 0.0
        for investment in self.investments:
            total_value += investment.security.price * investment.quantity
        return total_value

    def __to_dict__(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "owner": self.owner,
            "investments_count": len(self.investments),
        }
