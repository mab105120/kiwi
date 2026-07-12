import logging

from platform_common.logging import configure_logging

logger = logging.getLogger(__name__)


def main() -> None:
    configure_logging(service="worker")
    logger.info("worker starting")
    # TODO: poll the grading-job SQS queue (see
    # contracts/messages/grading-job.schema.json), dispatch each message to the
    # appropriate agent in app.agents based on jobType, and write results back.


if __name__ == "__main__":
    main()
