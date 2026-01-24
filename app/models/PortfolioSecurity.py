from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import db

if TYPE_CHECKING:
    # imports that are used only for type checking to avoid circular dependencies
    from app.models import Portfolio, User


class PortfolioSecurity(db.Model):
    __tablename__ = 'portfolio_security'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(Integer, ForeignKey('portfolio.id'), nullable=False)
    username: Mapped[str] = mapped_column(String(30), ForeignKey('user.username'), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)

    portfolio: Mapped['Portfolio'] = relationship('Portfolio', lazy='selectin')
    user: Mapped['User'] = relationship('User', lazy='selectin')

    # this is needed because PyLance cannot infer the constructor signature from SQLAlchemy's Mapped class
    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            portfolio_id: int | None = None,
            username: str | None = None,
            role: str | None = None,
        ) -> None: ...

    def __str__(self):
        return f'<PortfolioSecurity: id={self.id}; portfolio_id={self.portfolio_id}; username={self.username}; role={self.role}>'

    def __to_dict__(self):
        return {
            'id': self.id,
            'portfolio_id': self.portfolio_id,
            'username': self.username,
            'role': self.role,
        }
