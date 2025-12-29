from __future__ import annotations
from typing import List, TYPE_CHECKING
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import relationship, mapped_column, Mapped
from app.database import Base

if TYPE_CHECKING:
    from domain.Investment import Investment
    from domain.User import User

class Portfolio(Base):
    __tablename__ = 'portfolio'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    owner: Mapped[str] = mapped_column(String(30), ForeignKey('user.username'), nullable=False)

    investments: Mapped[List["Investment"]] = relationship(
        "Investment",
        back_populates="portfolio",
        lazy="selectin")

    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[owner],
        back_populates="portfolios",
        lazy="selectin")

    def __str__(self):
        user_str = getattr(self, 'user', None)
        username = user_str.username if user_str else "N/A"
        return f"<Portfolio: id={self.id}; name={self.name}; description={self.description}; user={username}; #investments={len(self.investments)}>"
    
    def get_portfolio_value(self) -> float:
        total_value = 0.0
        for investment in self.investments:
            total_value += investment.security.price * investment.quantity
        return total_value