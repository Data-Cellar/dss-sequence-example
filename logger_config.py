import coloredlogs
import logging

"""
Logging Configuration.

This module configures the application-wide logging settings, including log levels and output formatting.
"""


def setup_logging(level: str = "DEBUG") -> logging.Logger:
    """
    Configure logging for the application.

    Sets up colored logging and configures log levels for specific libraries
    to reduce noise.

    Args:
        level (str, optional): The default logging level (e.g., "DEBUG", "INFO", "WARNING"). Defaults to "DEBUG".

    Returns:
        logging.Logger: The configured logger instance named "mediator".
    """

    coloredlogs.install(level=level)
    logger = logging.getLogger("mediator")

    logging.getLogger("httpcore").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.INFO)

    return logger


logger = setup_logging(level="DEBUG")
