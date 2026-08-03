import logging
import time

from platform_common.logging import configure_logging

logger = logging.getLogger(__name__)


def main() -> None:
    configure_logging(service="worker")
    logger.info("worker starting")
    # TODO: poll the grading-job SQS queue (see
    # contracts/messages/grading-job.schema.json), dispatch each message to the
    # appropriate agent in worker_app.agents based on jobType, and write results back.

    # Phase-0 placeholder: keeps the process (and container health check) alive
    # until Phase 6 replaces this with the real polling loop.
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
