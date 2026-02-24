from __future__ import annotations

import logging

_LOGGING_CONFIGURED = False


def configure_logging(log_file: str = "chat.log") -> None:
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )
    _LOGGING_CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
