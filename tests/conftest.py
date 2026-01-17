from __future__ import annotations

import sys
from pathlib import Path
from typing import Generator

import pytest
from flask import Flask
from flask.testing import FlaskClient
from flask_sqlalchemy.session import Session
from sqlalchemy.orm import scoped_session

from app import create_app
from app.config import get_config
from app.db import db
from app.models import User
from app.service import alpha_vantage_client
from app.service.alpha_vantage_client import SecurityQuote

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope='session')
def app() -> Generator[Flask, None, None]:
    test_config = get_config('test')
    test_app = create_app(test_config)
    with test_app.app_context():
        db.create_all()
        _populate_database()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app) -> FlaskClient:
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app, monkeypatch) -> Generator[scoped_session[Session], None, None]:
    with app.app_context():
        connection = db.engine.connect()
        trans = connection.begin()

        test_session = scoped_session(db.session.session_factory)
        test_session.configure(bind=connection)
        test_session.__setattr__('tag', 'test_session')

        def mock_commit():
            print('Mocking commit. Replacing with flush')
            test_session.flush()

        monkeypatch.setattr(db, 'session', test_session, raising=True)
        monkeypatch.setattr(test_session, 'commit', mock_commit)
        monkeypatch.setattr(test_session, 'close', lambda: None)

        yield test_session

        test_session.remove()
        trans.rollback()
        connection.close()


@pytest.fixture
def mock_alpha_vantage(monkeypatch):
    def mock_get_quote(ticker: str) -> SecurityQuote | None:
        mock_data = {
            'AAPL': SecurityQuote(ticker='AAPL', issuer='Apple Inc.', price=150.00, date='2026-01-08'),
            'GOOGL': SecurityQuote(ticker='GOOGL', issuer='Alphabet Inc.', price=2800.00, date='2026-01-08'),
            'MSFT': SecurityQuote(ticker='MSFT', issuer='Microsoft Corp.', price=300.00, date='2026-01-08'),
            'TSLA': SecurityQuote(ticker='TSLA', issuer='Tesla Inc.', price=700.00, date='2026-01-08'),
        }
        return mock_data.get(ticker.upper())

    monkeypatch.setattr(alpha_vantage_client, 'get_quote', mock_get_quote)
    return mock_get_quote


@pytest.fixture
def mock_alpha_vantage_response():
    def _create_mock(response_data: dict):
        class MockResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return response_data

        return MockResponse()

    return _create_mock


def _populate_database():
    try:
        admin_user = User(
            username='admin',
            password='admin',
            firstname='Admin',
            lastname='User',
            balance=1000.00,
        )
        db.session.add(admin_user)
    except Exception:
        db.session.rollback()
    finally:
        db.session.commit()
