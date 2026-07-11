from flask import Flask, jsonify

from platform_common.errors import register_error_handlers
from platform_common.logging import configure_logging


def create_app() -> Flask:
    configure_logging(service="identity")

    app = Flask(__name__)
    register_error_handlers(app)

    # TODO: load config, init db session.

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok"), 200

    # TODO: register blueprints from app.routes here, mirroring
    # contracts/identity.openapi.yaml.

    return app
