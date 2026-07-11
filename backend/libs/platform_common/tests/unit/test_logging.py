import json
import logging

from platform_common.logging import configure_logging


def test_configure_logging_emits_one_json_object_per_line(capsys):
    configure_logging(service="test-service")

    logging.getLogger("test.module").info("hello world")

    line = capsys.readouterr().out.strip()
    payload = json.loads(line)

    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "test.module"
    assert payload["service"] == "test-service"
    assert "timestamp" in payload


def test_redacts_email_and_bearer_token_shaped_substrings(capsys):
    configure_logging(service="test-service")

    logging.getLogger("test.module").info(
        "user foo.bar@example.com authenticated with Bearer abc.def.ghi"
    )

    line = capsys.readouterr().out
    assert "foo.bar@example.com" not in line
    assert "abc.def.ghi" not in line


def test_redacts_sensitive_extra_fields_by_name(capsys):
    configure_logging(service="test-service")

    logging.getLogger("test.module").info(
        "login attempt", extra={"password": "hunter2", "email": "x@y.com"}
    )

    line = capsys.readouterr().out
    assert "hunter2" not in line
    assert "x@y.com" not in line


def test_configure_logging_is_idempotent(capsys):
    configure_logging(service="svc-a")
    configure_logging(service="svc-b")

    root = logging.getLogger()
    platform_common_handlers = [
        h for h in root.handlers if getattr(h, "_platform_common_handler", False)
    ]
    assert len(platform_common_handlers) == 1

    logging.getLogger("test.module").info("ping")
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["service"] == "svc-b"
