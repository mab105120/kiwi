from functools import wraps
from typing import Callable, List, Optional

from flask import current_app, g, jsonify, request

from app.db import db
from app.models import Portfolio, PortfolioPermission
from app.models.PortfolioPermission import PermissionLevel
from app.routes.domain import ErrorResponse


class AuthorizationError(Exception):
    pass


def get_user_portfolio_permission(username: str, portfolio_id: int) -> Optional[str]:
    """
    Get the permission level a user has for a portfolio.

    Returns:
        - 'owner' if the user owns the portfolio
        - 'manager' if the user has manager permission
        - 'viewer' if the user has viewer permission
        - None if the user has no access
    """
    portfolio = db.session.query(Portfolio).filter_by(id=portfolio_id).one_or_none()
    if not portfolio:
        return None

    if portfolio.owner == username:
        return 'owner'

    permission = (
        db.session.query(PortfolioPermission).filter_by(portfolio_id=portfolio_id, username=username).one_or_none()
    )
    if permission:
        return permission.permission_level

    return None


def require_self_access(username_param: str = 'username'):
    """
    Decorator that ensures the authenticated user can only access their own data.

    Args:
        username_param: The name of the route parameter or request body field containing the username.
                       Checks URL path parameters first, then query parameters, then JSON request body.
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            authenticated_username = g.user.get('username')

            # First try to get username from URL path parameters
            target_username = kwargs.get(username_param)

            # If not found in path, try to get from query parameters
            if target_username is None:
                target_username = request.args.get(username_param)

            # If not found in query params, try to get from JSON request body
            if target_username is None:
                json_data = request.get_json(silent=True)
                if json_data and isinstance(json_data, dict):
                    target_username = json_data.get(username_param)

            if target_username and target_username != authenticated_username:
                current_app.logger.warning(
                    f'Authorization denied: user {authenticated_username} attempted to access data for {target_username}'
                )
                error = ErrorResponse(
                    error_msg='Access denied: you can only access your own data',
                    request_id=g.get('request_id', 'N/A'),
                )
                return jsonify(error.model_dump()), 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def _convert_to_int(value, field_name: str):
    """
    Convert a value to an integer, returning the int or raising an error response tuple.

    Args:
        value: The value to convert (can be int, str, or other)
        field_name: The name of the field for error messages

    Returns:
        tuple: (converted_int, None) on success, or (None, error_response_tuple) on failure
    """
    if value is None:
        return None, None
    if isinstance(value, int):
        return value, None
    if isinstance(value, str):
        try:
            return int(value), None
        except ValueError:
            error = ErrorResponse(
                error_msg=f'Invalid {field_name} format: must be an integer',
                request_id=g.get('request_id', 'N/A'),
            )
            return None, (jsonify(error.model_dump()), 400)
    error = ErrorResponse(
        error_msg=f'Invalid {field_name} format: must be an integer',
        request_id=g.get('request_id', 'N/A'),
    )
    return None, (jsonify(error.model_dump()), 400)


def require_portfolio_permission(portfolio_id_param: str = 'portfolio_id', allowed_levels: List[str] = None):
    """
    Decorator that ensures the authenticated user has the required permission level for a portfolio.

    Args:
        portfolio_id_param: The name of the route parameter or request body field containing the portfolio ID.
                           Checks URL path parameters first, then query parameters, then JSON request body.
        allowed_levels: List of permission levels that are allowed (e.g., ['owner', 'manager', 'viewer']).
                       If None, defaults to ['owner', 'manager', 'viewer'] (any access).
    """
    if allowed_levels is None:
        allowed_levels = ['owner', PermissionLevel.MANAGER.value, PermissionLevel.VIEWER.value]

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            authenticated_username = g.user.get('username')

            # First try to get portfolio_id from URL path parameters (already an int from Flask)
            portfolio_id = kwargs.get(portfolio_id_param)

            # If not found in path, try to get from query parameters
            if portfolio_id is None:
                portfolio_id_str = request.args.get(portfolio_id_param)
                if portfolio_id_str is not None:
                    portfolio_id, error_response = _convert_to_int(portfolio_id_str, 'portfolio_id')
                    if error_response:
                        current_app.logger.warning(f'Invalid portfolio_id format in query params: {portfolio_id_str}')
                        return error_response

            # If not found in query params, try to get from JSON request body
            if portfolio_id is None:
                json_data = request.get_json(silent=True)
                if json_data and isinstance(json_data, dict):
                    raw_portfolio_id = json_data.get(portfolio_id_param)
                    if raw_portfolio_id is not None:
                        portfolio_id, error_response = _convert_to_int(raw_portfolio_id, 'portfolio_id')
                        if error_response:
                            current_app.logger.warning(f'Invalid portfolio_id format in JSON body: {raw_portfolio_id}')
                            return error_response

            if portfolio_id is None:
                current_app.logger.warning('Authorization check failed: portfolio_id not found in request')
                error = ErrorResponse(
                    error_msg='Portfolio ID is required',
                    request_id=g.get('request_id', 'N/A'),
                )
                return jsonify(error.model_dump()), 400

            permission = get_user_portfolio_permission(authenticated_username, portfolio_id)

            if permission is None:
                current_app.logger.warning(
                    f'Authorization denied: user {authenticated_username} has no access to portfolio {portfolio_id}'
                )
                error = ErrorResponse(
                    error_msg=f'Portfolio {portfolio_id} not found or access denied',
                    request_id=g.get('request_id', 'N/A'),
                )
                return jsonify(error.model_dump()), 404

            if permission not in allowed_levels:
                current_app.logger.warning(
                    f'Authorization denied: user {authenticated_username} has {permission} permission '
                    f'but needs one of {allowed_levels} for portfolio {portfolio_id}'
                )
                error = ErrorResponse(
                    error_msg='Access denied: insufficient permissions for this operation',
                    request_id=g.get('request_id', 'N/A'),
                )
                return jsonify(error.model_dump()), 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def check_portfolio_permission(username: str, portfolio_id: int, allowed_levels: List[str]) -> bool:
    """
    Helper function to check if a user has the required permission for a portfolio.

    Args:
        username: The username to check
        portfolio_id: The portfolio ID to check
        allowed_levels: List of permission levels that are allowed

    Returns:
        True if the user has one of the allowed permission levels, False otherwise
    """
    permission = get_user_portfolio_permission(username, portfolio_id)
    return permission is not None and permission in allowed_levels
