import pytest

from identity_app import create_app


@pytest.fixture
def client():
    return create_app().test_client()


def test_healthz_matches_contract(client):
    response = client.get("/identity/healthz")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
