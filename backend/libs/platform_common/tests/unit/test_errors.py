import pytest
from flask import Flask

from platform_common.errors import ApiError, register_error_handlers


@pytest.fixture
def client():
    app = Flask(__name__)
    register_error_handlers(app)

    @app.get("/boom-api-error")
    def boom_api_error():
        raise ApiError("nope", status_code=418, code="teapot")

    @app.get("/boom-generic")
    def boom_generic():
        raise RuntimeError("sensitive internal detail")

    return app.test_client()


def test_api_error_maps_to_its_status_and_body(client):
    response = client.get("/boom-api-error")

    assert response.status_code == 418
    assert response.get_json() == {"error": {"message": "nope", "code": "teapot"}}


def test_uncaught_exception_maps_to_generic_500(client):
    response = client.get("/boom-generic")

    assert response.status_code == 500
    assert response.get_json() == {
        "error": {"message": "internal server error", "code": "internal_error"}
    }
    assert "sensitive internal detail" not in response.get_data(as_text=True)
    assert "RuntimeError" not in response.get_data(as_text=True)
