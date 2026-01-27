from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import db

if TYPE_CHECKING:
    from app.models import Portfolio, User


class PermissionLevel(str, Enum):
    VIEWER = 'viewer'
    MANAGER = 'manager'


class PortfolioPermission(db.Model):
    __tablename__ = 'portfolio_permission'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(Integer, ForeignKey('portfolio.id'), nullable=False)
    username: Mapped[str] = mapped_column(String(30), ForeignKey('user.username'), nullable=False)
    permission_level: Mapped[str] = mapped_column(String(10), nullable=False)

    portfolio: Mapped['Portfolio'] = relationship(
        'Portfolio',
        foreign_keys=[portfolio_id],
        back_populates='permissions',
        lazy='selectin',
    )

    user: Mapped['User'] = relationship(
        'User',
        foreign_keys=[username],
        back_populates='portfolio_permissions',
        lazy='selectin',
    )

    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            portfolio_id: int,
            username: str,
            permission_level: str,
        ) -> None: ...

    def __str__(self):
        return (
            f'<PortfolioPermission: id={self.id}; portfolio_id={self.portfolio_id}; '
            f'username={self.username}; permission_level={self.permission_level}>'
        )

    def __to_dict__(self):
        return {
            'id': self.id,
            'portfolio_id': self.portfolio_id,
            'username': self.username,
            'permission_level': self.permission_level,
        }
