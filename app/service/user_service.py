from typing import List

from flask import current_app
from sqlalchemy.exc import IntegrityError

from app.db import db
from app.models.User import User


class UnsupportedUserOperationError(Exception):
    pass


def get_user_by_username(username: str) -> User | None:
    try:
        if not username:
            raise UnsupportedUserOperationError('Username cannot be empty')
        return db.session.query(User).filter_by(username=username).one_or_none()
    except Exception as e:
        db.session.rollback()
        raise UnsupportedUserOperationError(f'Failed to retrieve user due to error: {str(e)}')


def get_all_users() -> List[User]:
    try:
        current_app.logger.info('Retrieving all users from the database')
        users = db.session.query(User).all()
        current_app.logger.info(f'Retrieved {len(users)} users')
        return users
    except Exception as e:
        db.session.rollback()
        raise UnsupportedUserOperationError(f'Failed to retrieve users due to error: {str(e)}')


def update_user_balance(username: str, new_balance: float):
    try:
        user = db.session.query(User).filter_by(username=username).one_or_none()
        if not user:
            raise UnsupportedUserOperationError(f'User with username {username} does not exist')
        user.balance = new_balance
        db.session.flush()
    except Exception as e:
        db.session.rollback()
        raise UnsupportedUserOperationError(f'Failed to update user balance due to error: {str(e)}')


def create_user(username: str, firstname: str, lastname: str, balance: float):
    try:
        db.session.add(
            User(
                username=username,
                firstname=firstname,
                lastname=lastname,
                balance=balance,
            )
        )
        db.session.flush()
    except Exception as e:
        db.session.rollback()
        raise UnsupportedUserOperationError(f'Failed to create user due to error: {str(e)}')


def delete_user(username: str):
    if username == 'admin':
        raise UnsupportedUserOperationError('Cannot delete admin user')
    if not username:
        raise UnsupportedUserOperationError('Username cannot be empty')
    try:
        user = db.session.query(User).filter_by(username=username).one_or_none()
        if not user:
            raise UnsupportedUserOperationError(f'User with username {username} does not exist')
        db.session.delete(user)
        db.session.flush()
    except IntegrityError:
        raise UnsupportedUserOperationError(f'Cannot delete user {username} due to existing dependencies')
    except UnsupportedUserOperationError as e:
        raise e
    except Exception as e:
        db.session.rollback()
        raise UnsupportedUserOperationError(f'Failed to delete user due to error: {str(e)}')
