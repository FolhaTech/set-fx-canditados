import logging

import sys


def setup_logging(
        level: int = logging.INFO,
        format_string: str | None = None
) -> logging.Logger:
    if format_string is None:
        format_string = (
            "%(asctime)s  [%(levelname)-7s]  %(message)s"
        )

    # Handler configuration
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(format_string, datefmt="%H:%M:%S"))

    # Logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    for noisy in ["urllib3", "playwright", "asyncio"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return logging.getLogger("automacao")


# Get automation name for logger
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"automacao.{name}")
