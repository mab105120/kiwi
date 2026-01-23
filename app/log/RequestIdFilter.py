import logging

from flask import g


class RequestIdFilter(logging.Filter):
    """
    A logging filter that adds a request ID to log records.
    """

    def filter(self, record):
        record.request_id = getattr(g, 'request_id', 'unknown')
        return True
