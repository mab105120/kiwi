from flask import Flask

from platform_common.errors import register_error_handlers
from platform_common.logging import configure_logging

from api_app.routes.health import health_bp


def create_app() -> Flask:
    configure_logging(service="app-api")

    app = Flask(__name__)
    register_error_handlers(app)

    # TODO: load config, init db session.

    app.register_blueprint(health_bp)

    # TODO: register remaining blueprints from api_app.routes here, mirroring
    # contracts/app-api/openapi.yml.

    return app
