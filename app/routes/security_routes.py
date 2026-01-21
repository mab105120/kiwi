from flask import Blueprint, g, jsonify, request

import app.auth as auth
import app.routes.domain.request_schema as request_schema
import app.service.security_service as security_service
import app.service.transaction_service as transaction_service
from app.db import db
from app.routes.domain import ErrorResponse

security_bp = Blueprint('security', __name__)


@security_bp.route('/<ticker>', methods=['GET'])
@auth.requires_auth
def get_security(ticker):
    security_quote = security_service.get_security_by_ticker(ticker)
    if security_quote is None:
        error = ErrorResponse(
            error_msg=f'Security {ticker} not found or market data unavailable',
            request_id=g.get('request_id', 'N/A'),
        )
        return jsonify(error.model_dump()), 404
    return jsonify(
        {
            'ticker': security_quote.ticker,
            'issuer': security_quote.issuer,
            'price': security_quote.price,
            'date': security_quote.date,
        }
    ), 200


@security_bp.route('/purchase', methods=['POST'])
@auth.requires_auth
def execute_purchase_order():
    purchase_request = request_schema.ExecutePurchaseOrderRequest(**request.get_json())
    security_service.execute_purchase_order(
        portfolio_id=purchase_request.portfolio_id,
        ticker=purchase_request.ticker,
        quantity=purchase_request.quantity,
    )
    db.session.commit()
    return jsonify({'message': 'Purchase order executed successfully'}), 201


@security_bp.route('/<ticker>/transactions', methods=['GET'])
def get_security_transactions(ticker):
    transactions = transaction_service.get_transactions_by_ticker(ticker)
    return jsonify([transaction.__to_dict__() for transaction in transactions]), 200
