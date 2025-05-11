"""Error classes for the webhook receiver module.

This module defines custom error types for webhook processing to enable
structured error handling and recovery.
"""


class WebhookError(Exception):
    """Base class for all webhook errors."""
    pass


class ValidationError(WebhookError):
    """Error raised when webhook data fails validation."""
    pass


class ProcessingError(WebhookError):
    """Error raised when there's an error processing the webhook."""
    pass


class TransientError(WebhookError):
    """Error raised for temporary issues that may resolve with a retry."""
    pass


class NetworkError(TransientError):
    """Error raised for network-related issues."""
    pass


class ServiceUnavailableError(TransientError):
    """Error raised when a service is temporarily unavailable."""
    pass


class RateLimitError(TransientError):
    """Error raised when rate limits are exceeded."""
    pass


class CircuitBreakerError(WebhookError):
    """Error raised when the circuit breaker is open."""
    pass
