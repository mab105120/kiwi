from __future__ import annotations
from typing import List, TYPE_CHECKING
from database import Base
from sqlalchemy import String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from domain.Portfolio import Portfolio

class User(Base):
    __tablename__ = 'user'

    username: Mapped[str] = mapped_column(String(30), primary_key=True)
    password: Mapped[str] = mapped_column(String(30), nullable=False)
    firstname: Mapped[str] = mapped_column(String(30), nullable=False)
    lastname: Mapped[str] = mapped_column(String(30), nullable=False)
    balance: Mapped[float] = mapped_column(Float, nullable=False)

    portfolios: Mapped[List["Portfolio"]] = relationship(
        "Portfolio",
        back_populates="user",
        lazy="selectin")

    def __str__(self):
        return (
            f"<User: username='{self.username}'; "
            f"name='{self.firstname} {self.lastname}'; "
            f"#portfolios={len(self.portfolios)}; "
            f"balance={self.balance})"
        )
    