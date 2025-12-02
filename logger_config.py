import coloredlogs
import logging


def setup_logging(level: str = "DEBUG") -> logging.Logger:
    """
    Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, etc.)

    Returns:
        Configured logger
    """

    coloredlogs.install(level=level)
    logger = logging.getLogger("mediator")

    logging.getLogger("httpcore").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.INFO)

    return logger


logger = setup_logging(level="DEBUG")
