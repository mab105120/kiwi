from flask import Flask, jsonify


def create_app() -> Flask:
    app = Flask(__name__)

    # TODO: load config, init db session, register error handlers.

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok"), 200

    # TODO: register blueprints from app.routes here, mirroring
    # contracts/app-api.openapi.yaml.

    return app
