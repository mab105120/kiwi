from flask import Blueprint, current_app, g, jsonify

import app.service.security_service as security_service
import app.service.transaction_service as transaction_service
from app.routes.domain import ErrorResponse

security_bp = Blueprint('security', __name__)


@security_bp.route('/<ticker>', methods=['GET'])
def get_security(ticker):
    current_app.logger.info(f'Retrieving security: {ticker}')
    try:
        security_quote = security_service.get_security_by_ticker(ticker)
        if security_quote is None:
            current_app.logger.warning(f'Security not found or market data unavailable: {ticker}')
            error = ErrorResponse(
                error_msg=f'Security {ticker} not found or market data unavailable',
                request_id=g.get('request_id', 'N/A'),
            )
            return jsonify(error.model_dump()), 404
        current_app.logger.debug(f'Successfully retrieved security: {ticker}, price: ${security_quote.price}')
        return jsonify(
            {
                'ticker': security_quote.ticker,
                'issuer': security_quote.issuer,
                'price': security_quote.price,
                'date': security_quote.date,
            }
        ), 200
    except Exception as e:
        current_app.logger.error(f'Failed to retrieve security {ticker}: {str(e)}')
        raise


@security_bp.route('/<ticker>/transactions', methods=['GET'])
def get_security_transactions(ticker):
    current_app.logger.info(f'Retrieving transactions for security: {ticker}')
    try:
        transactions = transaction_service.get_transactions_by_ticker(ticker)
        current_app.logger.debug(f'Successfully retrieved {len(transactions)} transactions for security: {ticker}')
        return jsonify([transaction.__to_dict__() for transaction in transactions]), 200
    except Exception as e:
        current_app.logger.error(f'Failed to retrieve transactions for security {ticker}: {str(e)}')
        raise
