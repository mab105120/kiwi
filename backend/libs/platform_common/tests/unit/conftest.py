import logging

import pytest


@pytest.fixture(autouse=True)
def _reset_root_logger():
    """Isolate each test's root logger state so configure_logging()'s
    idempotency doesn't leak handlers (bound to a prior test's captured
    stdout) across tests."""
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    root.handlers = []
    yield
    root.handlers = original_handlers
    root.setLevel(original_level)
