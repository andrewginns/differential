"""Tests for the webhook error classes."""

from newsletter_generator.whatsapp.webhook_errors import (
    WebhookError,
    ValidationError,
    ProcessingError,
    TransientError,
    NetworkError,
    ServiceUnavailableError,
    RateLimitError,
    CircuitBreakerError,
)


class TestWebhookErrors:
    """Test cases for the webhook error classes."""

    def test_error_hierarchy(self):
        """Test that the error hierarchy is correct."""
        assert issubclass(ValidationError, WebhookError)
        assert issubclass(ProcessingError, WebhookError)
        assert issubclass(TransientError, WebhookError)
        assert issubclass(NetworkError, TransientError)
        assert issubclass(ServiceUnavailableError, TransientError)
        assert issubclass(RateLimitError, TransientError)
        assert issubclass(CircuitBreakerError, WebhookError)
        
    def test_error_instantiation(self):
        """Test that errors can be instantiated with a message."""
        error = ValidationError("Invalid payload")
        assert str(error) == "Invalid payload"
        
        error = ProcessingError("Error processing webhook")
        assert str(error) == "Error processing webhook"
        
        error = TransientError("Temporary error")
        assert str(error) == "Temporary error"
        
        error = NetworkError("Network error")
        assert str(error) == "Network error"
        
        error = ServiceUnavailableError("Service unavailable")
        assert str(error) == "Service unavailable"
        
        error = RateLimitError("Rate limit exceeded")
        assert str(error) == "Rate limit exceeded"
        
        error = CircuitBreakerError("Circuit breaker open")
        assert str(error) == "Circuit breaker open"
    
    def test_error_catching(self):
        """Test that errors can be caught by their parent types."""
        try:
            raise ValidationError("Invalid payload")
        except WebhookError as e:
            assert str(e) == "Invalid payload"
        
        try:
            raise NetworkError("Network error")
        except TransientError as e:
            assert str(e) == "Network error"
        
        try:
            raise NetworkError("Network error")
        except WebhookError as e:
            assert str(e) == "Network error"
        
        errors_caught = 0
        for error_class in [ValidationError, ProcessingError, NetworkError]:
            try:
                raise error_class("Test error")
            except WebhookError:
                errors_caught += 1
        
        assert errors_caught == 3
