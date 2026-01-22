from flask import Blueprint, current_app, g, jsonify, request

import app.routes.domain.request_schema as request_schema
import app.service.transaction_service as transaction_service
import app.service.user_service as user_service
from app.db import db
from app.routes.domain import ErrorResponse

user_bp = Blueprint('user', __name__)


@user_bp.route('/', methods=['GET'])
def get_users():
    current_app.logger.info(f'User {g.user["username"]} requested all users')
    users = user_service.get_all_users()
    return jsonify([user.__to_dict__() for user in users]), 200


@user_bp.route('/<username>', methods=['GET'])
def get_user(username):
    user = user_service.get_user_by_username(username)
    if user is None:
        error = ErrorResponse(
            error_msg=f'User {username} not found',
            request_id=g.get('request_id', 'N/A'),
        )
        return jsonify(error.model_dump()), 404
    return jsonify(user.__to_dict__()), 200


@user_bp.route('/', methods=['POST'])
def create_user():
    create_user_request = request_schema.CreateUserRequest(**request.get_json())
    user_service.create_user(**create_user_request.model_dump())
    db.session.commit()
    return jsonify({'message': 'User created successfully'}), 201


@user_bp.route('/update-balance', methods=['PUT'])
def update_balance():
    update_balance_request = request_schema.UpdateUserBalanceRequest(**request.get_json())
    user_service.update_user_balance(**update_balance_request.model_dump())
    db.session.commit()
    return jsonify({'message': 'User balance updated successfully'}), 200


@user_bp.route('/<username>', methods=['DELETE'])
def delete_user(username):
    user_service.delete_user(username)
    db.session.commit()
    return jsonify({'message': 'User deleted successfully'}), 200


@user_bp.route('/<username>/transactions', methods=['GET'])
def get_user_transactions(username):
    transactions = transaction_service.get_transactions_by_user(username)
    return jsonify([transaction.__to_dict__() for transaction in transactions]), 200
