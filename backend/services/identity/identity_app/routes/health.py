from flask import Blueprint, current_app, jsonify

health_bp = Blueprint("health", __name__, url_prefix="/identity")


@health_bp.get("/healthz")
def healthz():
    current_app.logger.info("healthz check")
    return jsonify(status="ok"), 200
