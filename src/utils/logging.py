"""Structured logging utilities."""

import logging
import json
from typing import Any, Optional


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Set up structured logging and return logger."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def log_event(logger: logging.Logger, event: str, **kwargs: Any) -> None:
    """Log a structured event."""
    context = {k: v for k, v in kwargs.items() if v is not None}
    logger.info(f"{event} {json.dumps(context)}")

