from flask import Blueprint, current_app, g, jsonify, request

import app.routes.domain.request_schema as request_schema
import app.service.transaction_service as transaction_service
import app.service.user_service as user_service
from app.db import db
from app.routes.domain import ErrorResponse

user_bp = Blueprint('user', __name__)


@user_bp.route('/', methods=['GET'])
def get_users():
    current_app.logger.info('Retrieving all users')
    try:
        users = user_service.get_all_users()
        current_app.logger.debug(f'Successfully retrieved {len(users)} users')
        return jsonify([user.__to_dict__() for user in users]), 200
    except Exception as e:
        current_app.logger.error(f'Failed to retrieve users: {str(e)}')
        raise


@user_bp.route('/<username>', methods=['GET'])
def get_user(username):
    current_app.logger.info(f'Retrieving user: {username}')
    try:
        user = user_service.get_user_by_username(username)
        if user is None:
            current_app.logger.warning(f'User not found: {username}')
            error = ErrorResponse(
                error_msg=f'User {username} not found',
                request_id=g.get('request_id', 'N/A'),
            )
            return jsonify(error.model_dump()), 404
        current_app.logger.debug(f'Successfully retrieved user: {username}')
        return jsonify(user.__to_dict__()), 200
    except Exception as e:
        current_app.logger.error(f'Failed to retrieve user {username}: {str(e)}')
        raise


@user_bp.route('/', methods=['POST'])
def create_user():
    create_user_request = request_schema.CreateUserRequest(**request.get_json())
    current_app.logger.info(f'Creating user: {create_user_request.username}')
    try:
        user_service.create_user(**create_user_request.model_dump())
        db.session.commit()
        current_app.logger.info(
            f'Successfully created user: {create_user_request.username}, balance: {create_user_request.balance}'
        )
        return jsonify({'message': 'User created successfully'}), 201
    except Exception as e:
        current_app.logger.error(f'Failed to create user {create_user_request.username}: {str(e)}')
        raise


@user_bp.route('/update-balance', methods=['PUT'])
def update_balance():
    update_balance_request = request_schema.UpdateUserBalanceRequest(**request.get_json())
    current_app.logger.info(
        f'Updating balance for user: {update_balance_request.username}, '
        f'new balance: {update_balance_request.new_balance}'
    )
    try:
        user_service.update_user_balance(**update_balance_request.model_dump())
        db.session.commit()
        current_app.logger.info(f'Successfully updated balance for user: {update_balance_request.username}')
        return jsonify({'message': 'User balance updated successfully'}), 200
    except Exception as e:
        current_app.logger.error(f'Failed to update balance for user {update_balance_request.username}: {str(e)}')
        raise


@user_bp.route('/<username>', methods=['DELETE'])
def delete_user(username):
    current_app.logger.info(f'Deleting user: {username}')
    try:
        user_service.delete_user(username)
        db.session.commit()
        current_app.logger.info(f'Successfully deleted user: {username}')
        return jsonify({'message': 'User deleted successfully'}), 200
    except Exception as e:
        current_app.logger.error(f'Failed to delete user {username}: {str(e)}')
        raise


@user_bp.route('/<username>/transactions', methods=['GET'])
def get_user_transactions(username):
    current_app.logger.info(f'Retrieving transactions for user: {username}')
    try:
        transactions = transaction_service.get_transactions_by_user(username)
        current_app.logger.debug(f'Successfully retrieved {len(transactions)} transactions for user: {username}')
        return jsonify([transaction.__to_dict__() for transaction in transactions]), 200
    except Exception as e:
        current_app.logger.error(f'Failed to retrieve transactions for user {username}: {str(e)}')
        raise
