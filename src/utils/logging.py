"""Enhanced structured logging utilities with correlation IDs, performance timing, and sensitive data handling."""

import logging
import json
import time
import uuid
import re
import hashlib
from typing import Any, Optional, Dict, Callable
from contextlib import contextmanager
from functools import wraps
from datetime import datetime, timezone

from src.utils.logging_config import LoggingConfig, get_logger


# Thread-local storage for correlation ID (using contextvars for async support)
try:
    from contextvars import ContextVar
    _correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
except ImportError:
    # Fallback for Python < 3.7
    from threading import local
    _local = local()
    _correlation_id_var = None


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for request tracing."""
    return f"req_{uuid.uuid4().hex[:12]}"


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID from context."""
    if _correlation_id_var is not None:
        return _correlation_id_var.get()
    return getattr(_local, 'correlation_id', None)


def set_correlation_id(correlation_id: Optional[str]) -> None:
    """Set the correlation ID in context."""
    if _correlation_id_var is not None:
        _correlation_id_var.set(correlation_id)
    else:
        _local.correlation_id = correlation_id


@contextmanager
def correlation_context(correlation_id: Optional[str] = None):
    """Context manager for correlation ID propagation."""
    if correlation_id is None:
        correlation_id = generate_correlation_id()
    
    old_id = get_correlation_id()
    set_correlation_id(correlation_id)
    try:
        yield correlation_id
    finally:
        set_correlation_id(old_id)


def mask_sensitive_data(text: str) -> str:
    """Mask sensitive data in text (PII, tokens, etc.)."""
    if not text or not LoggingConfig.LOG_MASK_SENSITIVE:
        return text
    
    # Mask email addresses
    text = re.sub(
        r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}',
        '[REDACTED_EMAIL]',
        text,
        flags=re.IGNORECASE
    )
    
    # Mask phone numbers
    text = re.sub(
        r'\b\+?\d[\d\s().-]{7,}\b',
        '[REDACTED_PHONE]',
        text
    )
    
    # Mask API keys/tokens (common patterns)
    text = re.sub(
        r'(?i)(api[_-]?key|token|secret|password|auth)[\s:=]+([A-Za-z0-9_-]{20,})',
        r'\1=[REDACTED]',
        text
    )
    
    # Mask Slack tokens
    text = re.sub(
        r'xox[baprs]-[A-Za-z0-9-]+',
        '[REDACTED_SLACK_TOKEN]',
        text,
        flags=re.IGNORECASE
    )
    
    return text


def mask_user_id(user_id: str) -> str:
    """Mask or hash user ID for privacy."""
    if not LoggingConfig.LOG_MASK_SENSITIVE or not user_id:
        return user_id
    
    # Hash the user ID and return first 8 chars + last 4 chars
    if len(user_id) > 12:
        hashed = hashlib.sha256(user_id.encode()).hexdigest()[:8]
        return f"{user_id[:4]}...{hashed}"
    return user_id


def sanitize_message_text(text: str, max_length: int = 500) -> Optional[str]:
    """Sanitize message text for logging."""
    if not LoggingConfig.LOG_MESSAGE_CONTENT:
        return None
    
    if not text:
        return None
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    # Mask sensitive data
    if LoggingConfig.LOG_MASK_SENSITIVE:
        text = mask_sensitive_data(text)
    
    return text


class StructuredLogger:
    """Enhanced logger with structured logging support."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def _get_extra(self, **kwargs: Any) -> Dict[str, Any]:
        """Build extra fields for structured logging."""
        extra = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Add correlation ID if available
        correlation_id = get_correlation_id()
        if correlation_id:
            extra["correlation_id"] = correlation_id
        
        # Add any provided kwargs
        extra.update(kwargs)
        
        return extra
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with structured fields."""
        self.logger.debug(message, extra=self._get_extra(**kwargs))
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with structured fields."""
        self.logger.info(message, extra=self._get_extra(**kwargs))
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with structured fields."""
        self.logger.warning(message, extra=self._get_extra(**kwargs))
    
    def error(self, message: str, exc_info: bool = False, **kwargs: Any) -> None:
        """Log error message with structured fields."""
        self.logger.error(message, extra=self._get_extra(**kwargs), exc_info=exc_info)
    
    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with structured fields."""
        self.logger.exception(message, extra=self._get_extra(**kwargs))


def get_structured_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(get_logger(name))


@contextmanager
def log_timing(operation_name: str, logger: Optional[StructuredLogger] = None, **context: Any):
    """Context manager for timing operations."""
    if logger is None:
        logger = get_structured_logger(__name__)
    
    start_time = time.time()
    logger.debug(f"Starting {operation_name}", operation=operation_name, **context)
    
    try:
        yield
    finally:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Completed {operation_name}",
            operation=operation_name,
            processing_time_ms=round(elapsed_ms, 2),
            **context
        )
        
        # Log slow operations as warning
        if elapsed_ms > LoggingConfig.LOG_SLOW_OPERATION_THRESHOLD_MS:
            logger.warning(
                f"Slow operation detected: {operation_name}",
                operation=operation_name,
                processing_time_ms=round(elapsed_ms, 2),
                threshold_ms=LoggingConfig.LOG_SLOW_OPERATION_THRESHOLD_MS,
                **context
            )


def timed(operation_name: Optional[str] = None, logger: Optional[StructuredLogger] = None):
    """Decorator for timing function calls."""
    def decorator(func: Callable) -> Callable:
        op_name = operation_name or f"{func.__module__}.{func.__name__}"
        log = logger or get_structured_logger(func.__module__)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with log_timing(op_name, logger=log):
                return func(*args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with log_timing(op_name, logger=log):
                return await func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Set up structured logging and return logger (legacy compatibility)."""
    LoggingConfig.setup_logging()
    return get_logger(__name__)


def log_event(logger: logging.Logger, event: str, **kwargs: Any) -> None:
    """Log a structured event (legacy compatibility)."""
    structured_logger = StructuredLogger(logger)
    structured_logger.info(event, **kwargs)
