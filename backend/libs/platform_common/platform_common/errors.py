import logging

from flask import Flask, jsonify

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Shared error envelope matching the error shape defined in contracts/."""

    def __init__(self, message: str, status_code: int = 400, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code

    def to_dict(self) -> dict:
        return {
            "error": {
                "message": self.message,
                "code": self.code,
            }
        }


def register_error_handlers(app: Flask) -> None:
    """Map ApiError to its shaped response and everything else to a generic
    500 that never leaks a stack trace or exception message to the client
    (constitution S-5)."""

    @app.errorhandler(ApiError)
    def _handle_api_error(err: ApiError):
        return jsonify(err.to_dict()), err.status_code

    @app.errorhandler(Exception)
    def _handle_uncaught_exception(err: Exception):
        logger.exception("Unhandled exception")
        return jsonify(
            {"error": {"message": "internal server error", "code": "internal_error"}}
        ), 500
