from flask import Blueprint, current_app, g, jsonify, request

import app.routes.domain.request_schema as request_schema
import app.service.portfolio_service as portfolio_service
import app.service.transaction_service as transaction_service
import app.service.user_service as user_service
from app.db import db
from app.routes.domain import ErrorResponse

portfolio_bp = Blueprint('portfolio', __name__)


@portfolio_bp.route('/', methods=['GET'])
def get_all_portfolios():
    current_app.logger.info('Retrieving all portfolios')
    try:
        portfolios = portfolio_service.get_all_portfolios()
        current_app.logger.debug(f'Successfully retrieved {len(portfolios)} portfolios')
        return jsonify([portfolio.__to_dict__() for portfolio in portfolios]), 200
    except Exception as e:
        current_app.logger.error(f'Failed to retrieve portfolios: {str(e)}')
        raise


@portfolio_bp.route('/<int:portfolio_id>', methods=['GET'])
def get_portfolio(portfolio_id):
    current_app.logger.info(f'Retrieving portfolio: {portfolio_id}')
    try:
        portfolio = portfolio_service.get_portfolio_by_id(portfolio_id)
        if portfolio is None:
            current_app.logger.warning(f'Portfolio not found: {portfolio_id}')
            error = ErrorResponse(
                error_msg=f'Portfolio {portfolio_id} not found',
                request_id=g.get('request_id', 'N/A'),
            )
            return jsonify(error.model_dump()), 404
        current_app.logger.debug(f'Successfully retrieved portfolio: {portfolio_id}')
        return jsonify(portfolio.__to_dict__()), 200
    except Exception as e:
        current_app.logger.error(f'Failed to retrieve portfolio {portfolio_id}: {str(e)}')
        raise


@portfolio_bp.route('/user/<username>', methods=['GET'])
def get_portfolios_by_user(username):
    current_app.logger.info(f'Retrieving portfolios for user: {username}')
    try:
        user = user_service.get_user_by_username(username)
        if user is None:
            current_app.logger.warning(f'User not found: {username}')
            error = ErrorResponse(
                error_msg=f'User {username} not found',
                request_id=g.get('request_id', 'N/A'),
            )
            return jsonify(error.model_dump()), 404
        portfolios = portfolio_service.get_portfolios_by_user(user)
        current_app.logger.debug(f'Successfully retrieved {len(portfolios)} portfolios for user: {username}')
        return jsonify([portfolio.__to_dict__() for portfolio in portfolios]), 200
    except Exception as e:
        current_app.logger.error(f'Failed to retrieve portfolios for user {username}: {str(e)}')
        raise


@portfolio_bp.route('/', methods=['POST'])
def create_portfolio():
    create_portfolio_request = request_schema.CreatePortfolioRequest(**request.get_json())
    current_app.logger.info(
        f'Creating portfolio: {create_portfolio_request.name} for user: {create_portfolio_request.username}'
    )
    try:
        user = user_service.get_user_by_username(create_portfolio_request.username)
        if user is None:
            current_app.logger.warning(f'User not found: {create_portfolio_request.username}')
            error = ErrorResponse(
                error_msg=f'User {create_portfolio_request.username} not found',
                request_id=g.get('request_id', 'N/A'),
            )
            return jsonify(error.model_dump()), 404
        portfolio_id = portfolio_service.create_portfolio(
            name=create_portfolio_request.name,
            description=create_portfolio_request.description,
            user=user,
        )
        db.session.commit()
        current_app.logger.info(
            f'Successfully created portfolio: {create_portfolio_request.name} (ID: {portfolio_id}) '
            f'for user: {create_portfolio_request.username}'
        )
        return jsonify({'message': 'Portfolio created successfully', 'portfolio_id': portfolio_id}), 201
    except Exception as e:
        current_app.logger.error(
            f'Failed to create portfolio {create_portfolio_request.name} '
            f'for user {create_portfolio_request.username}: {str(e)}'
        )
        raise


@portfolio_bp.route('/<int:portfolio_id>', methods=['DELETE'])
def delete_portfolio(portfolio_id):
    current_app.logger.info(f'Deleting portfolio: {portfolio_id}')
    try:
        portfolio_service.delete_portfolio(portfolio_id)
        db.session.commit()
        current_app.logger.info(f'Successfully deleted portfolio: {portfolio_id}')
        return jsonify({'message': 'Portfolio deleted successfully'}), 200
    except Exception as e:
        current_app.logger.error(f'Failed to delete portfolio {portfolio_id}: {str(e)}')
        raise


@portfolio_bp.route('/<int:portfolio_id>/liquidate/', methods=['POST'])
def liquidate_investment(portfolio_id):
    liquidate_request = request_schema.LiquidateInvestmentRequest(**request.get_json())
    current_app.logger.info(
        f'Liquidating investment in portfolio {portfolio_id}: '
        f'{liquidate_request.quantity} shares of {liquidate_request.ticker}'
    )
    try:
        portfolio_service.liquidate_investment(
            portfolio_id=portfolio_id,
            ticker=liquidate_request.ticker,
            quantity=liquidate_request.quantity,
        )
        db.session.commit()
        current_app.logger.info(
            f'Successfully liquidated {liquidate_request.quantity} shares of {liquidate_request.ticker} '
            f'from portfolio {portfolio_id}'
        )
        return jsonify({'message': 'Investment liquidated successfully'}), 200
    except Exception as e:
        current_app.logger.error(
            f'Failed to liquidate {liquidate_request.quantity} shares of {liquidate_request.ticker} '
            f'from portfolio {portfolio_id}: {str(e)}'
        )
        raise


@portfolio_bp.route('/<int:portfolio_id>/transactions', methods=['GET'])
def get_portfolio_transactions(portfolio_id):
    current_app.logger.info(f'Retrieving transactions for portfolio: {portfolio_id}')
    try:
        transactions = transaction_service.get_transactions_by_portfolio_id(portfolio_id)
        current_app.logger.debug(
            f'Successfully retrieved {len(transactions)} transactions for portfolio: {portfolio_id}'
        )
        return jsonify([transaction.__to_dict__() for transaction in transactions]), 200
    except Exception as e:
        current_app.logger.error(f'Failed to retrieve transactions for portfolio {portfolio_id}: {str(e)}')
        raise
