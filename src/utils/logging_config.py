"""Centralized logging configuration with environment variable support."""

import os
import logging
import sys
from typing import Optional
from pythonjsonlogger import jsonlogger


class LoggingConfig:
    """Centralized logging configuration."""
    
    # Environment variable defaults
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
    LOG_FORMAT = os.environ.get("LOG_FORMAT", "json").lower()
    LOG_MESSAGE_CONTENT = os.environ.get("LOG_MESSAGE_CONTENT", "true").lower() == "true"
    LOG_MASK_SENSITIVE = os.environ.get("LOG_MASK_SENSITIVE", "true").lower() == "true"
    LOG_CORRELATION_ID_HEADER = os.environ.get("LOG_CORRELATION_ID_HEADER", "X-Correlation-ID")
    LOG_SLOW_OPERATION_THRESHOLD_MS = int(os.environ.get("LOG_SLOW_OPERATION_THRESHOLD_MS", "1000"))
    
    @classmethod
    def setup_logging(cls) -> None:
        """Configure logging based on environment variables."""
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, cls.LOG_LEVEL, logging.INFO))
        
        # Remove existing handlers
        root_logger.handlers.clear()
        
        # Create handler (stdout for serverless/Vercel)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, cls.LOG_LEVEL, logging.INFO))
        
        # Set formatter based on LOG_FORMAT
        if cls.LOG_FORMAT == "json":
            formatter = jsonlogger.JsonFormatter(
                "%(timestamp)s %(level)s %(name)s %(message)s",
                timestamp=True
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        
        # Suppress noisy third-party loggers
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("supabase").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)


