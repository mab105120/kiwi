from __future__ import annotations
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
from typing import Generator
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

import app.database as db
from app.database import Base
from app.models import User, Security


@pytest.fixture(scope="session")
def engine():
    """
    create an in-memory database that is available for use in the entire test session.
    initialize the database with tables.
    """
    eng = create_engine(
        "sqlite+pysqlite:///:memory:",
        future = True,
        echo = False
    )

    # initialize all database objects
    Base.metadata.create_all(eng)

    yield eng
    eng.dispose()

@pytest.fixture(scope="session")
def connection(engine):
    with engine.connect() as conn:
        yield conn


@pytest.fixture(scope="function")
def db_session(connection, monkeypatch) -> Generator[Session]:
    trans = connection.begin()
    
    TestingSessionLocal = sessionmaker(
        bind=connection,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False
    )

    session = TestingSessionLocal()
    _populate_database(session)

    monkeypatch.setattr(db, 'get_session', lambda: session, raising=True)

    try:
        yield session
    finally:
        trans.rollback()
        session.close()
        
def _populate_database(session):
    try:
        admin_user = User(
            username='admin',
            password='admin',
            firstname='Admin',
            lastname='User',
            balance=1000.00
        )
        session.add(admin_user)

        securities = [
            Security(ticker="AAPL", issuer="Apple Inc.", price=150.00),
            Security(ticker="GOOGL", issuer="Alphabet Inc.", price=2800.00),
            Security(ticker="MSFT", issuer="Microsoft Corp.", price=300.00)
        ]
        session.add_all(securities)
    except Exception:
        session.rollback()
    finally:
        session.commit()