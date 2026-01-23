import datetime
import logging
import sys
import uuid
from logging.handlers import RotatingFileHandler
from zoneinfo import ZoneInfo

from flask import Flask, g, jsonify, request
from flask_caching import Cache
from pydantic import ValidationError

from app import auth
from app.auth import CognitoTokenValidator
from app.db import db
from app.log.RequestIdFilter import RequestIdFilter
from app.routes import portfolio_bp, security_bp, user_bp
from app.routes.domain import ErrorResponse
from app.service import cognito_client, user_service

# Initialize Flask-Caching
cache = Cache()


def create_app(config):
    try:
        app = Flask(__name__)
        app.config.from_object(config)

        # Configure Flask-Caching
        app.config['CACHE_TYPE'] = 'simple'
        app.config['CACHE_DEFAULT_TIMEOUT'] = 300
        cache.init_app(app)

        # configure authentication
        cognito_validator = CognitoTokenValidator(
            region=app.config['COGNITO_REGION'],
            user_pool_id=app.config['COGNITO_USER_POOL_ID'],
            app_client_id=app.config['COGNITO_APP_CLIENT_ID'],
        )
        app.config['COGNITO_VALIDATOR'] = cognito_validator
        # configure logging
        with app.app_context():
            if not app.testing:
                app.logger.handlers.clear()
                if app.debug or app.testing:
                    handler = logging.StreamHandler(sys.stdout)
                else:
                    handler = RotatingFileHandler('app.log', maxBytes=100000, backupCount=10)
                handler.setLevel(logging.INFO)
                formatter = logging.Formatter(
                    '%(asctime)s [%(request_id)s] %(levelname)s: %(message)s (in %(module)s:%(lineno)d)'
                )
                handler.setFormatter(formatter)
                handler.addFilter(RequestIdFilter())
                app.logger.addHandler(handler)
                app.logger.setLevel(logging.DEBUG if app.debug else logging.INFO)
                app.logger.info('Starting app..')

        @app.before_request
        def before_request():
            g.request_id = str(uuid.uuid4())
            g.request_start_time = datetime.datetime.now(ZoneInfo('America/New_York'))
            app.logger.info(
                f'New request: @{request.method} {request.host}{request.path} args: {request.args.to_dict()} '
            )
            # authenticate request caller
            token = auth.get_token_from_header()
            if not token:
                app.logger.warning('Missing authorization token')
                error = ErrorResponse(
                    error_msg='Missing authorization token',
                    request_id=g.request_id,
                )
                return jsonify(error.model_dump()), 401
            validator = app.config.get('COGNITO_VALIDATOR')
            if not validator:
                error = ErrorResponse(
                    error_msg='Server configuration error: Token validator not configured',
                    request_id=g.request_id,
                )
                return jsonify(error.model_dump()), 500
            try:
                app.logger.info('Validating access token')
                claims = validator.validate_token(token)
                g.user = {
                    'user_id': claims.get('sub'),
                    'username': claims.get('username'),
                    'email': claims.get('email'),
                    'token_expiry': claims.get('exp'),
                    'claims': claims,
                }
                app.logger.info(f'Token successfully validated. Authenticated user: {g.user["username"]}')

            except Exception as e:
                app.logger.warning(f'Invalid token: {str(e)}')
                error = ErrorResponse(
                    error_msg=f'Invalid token: {str(e)}',
                    request_id=g.request_id,
                )
                return jsonify(error.model_dump()), 401

            # create user if first time request
            if cache.get('pre_request_all_users') is None:
                users = user_service.get_all_users()
                cache.set('pre_request_all_users', users, timeout=60)
            users = cache.get('pre_request_all_users')
            caller_username = g.user['username']
            caller_user = next((u for u in users if u.username == caller_username), None)
            try:
                if not caller_user:
                    user_info = cognito_client.get_user_info(token)
                    firstname = user_info['attributes'].get('given_name', None)
                    lastname = user_info['attributes'].get('family_name', None)
                    app.logger.info(f'Creating new user record for {caller_username}')
                    user_service.create_user(
                        username=caller_username,
                        firstname=firstname,
                        lastname=lastname,
                        balance=0.00,
                    )
                    db.session.commit()
                    app.logger.info('Refreshing cache')
                    users = user_service.get_all_users()
                    cache.set('all_users', users, timeout=60)
            except Exception as e:
                app.logger.error(f'Error creating user: {str(e)}')

        @app.after_request
        def after_request(response):
            request_end_time = datetime.datetime.now(ZoneInfo('America/New_York'))
            duration = (request_end_time - g.request_start_time).total_seconds()
            app.logger.info(f'Request completed in {duration} seconds with {response.status}')
            return response

        @app.errorhandler(Exception)
        def error_handler(e):
            db.session.rollback()
            app.logger.error(
                f'Unhandled exception caught by the global error handler: {str(e)}',
                exc_info=True,
            )
            error = ErrorResponse(
                error_msg=f'Internal server error: {str(e)}',
                request_id=g.get('request_id', 'N/A'),
            )
            return jsonify(error.model_dump()), 500

        @app.errorhandler(ValidationError)
        def validation_error_handler(e):
            app.logger.warning(f'Pydantic validation error: {str(e)}')
            error = ErrorResponse(
                error_msg=f'Invalid request data: {str(e)}',
                request_id=g.get('request_id', 'N/A'),
            )
            return jsonify(error.model_dump()), 400

        @app.teardown_appcontext
        def tear_down(exception=None):
            if exception:
                db.session.rollback()
            db.session.remove()

        # register extensions
        db.init_app(app)

        # register blueprints
        app.register_blueprint(user_bp, url_prefix='/users')
        app.register_blueprint(portfolio_bp, url_prefix='/portfolios')
        app.register_blueprint(security_bp, url_prefix='/securities')

        return app
    except Exception as e:
        print(f'Error creating app: {e}')
        raise
