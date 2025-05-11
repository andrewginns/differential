"""Tests for the circuit breaker implementation."""

import pytest
import time
from unittest.mock import patch, MagicMock

from newsletter_generator.whatsapp.webhook_receiver import (
    CircuitBreaker,
    circuit_breaker_decorator,
)
from newsletter_generator.whatsapp.webhook_errors import (
    CircuitBreakerError,
    TransientError,
)


class TestCircuitBreaker:
    """Test cases for the CircuitBreaker class."""

    def test_initial_state(self):
        """Test that the circuit breaker starts in the closed state."""
        cb = CircuitBreaker()
        assert cb.state == "closed"
        assert cb.failure_count == 0
        assert cb.can_execute() is True
    
    def test_record_failure(self):
        """Test that recording failures increments the failure count."""
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.failure_count == 0
        
        cb.record_failure()
        assert cb.failure_count == 1
        assert cb.state == "closed"
        
        cb.record_failure()
        assert cb.failure_count == 2
        assert cb.state == "closed"
    
    def test_open_circuit(self):
        """Test that the circuit opens after reaching the failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)
        
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "closed"
        
        cb.record_failure()
        assert cb.state == "open"
        assert cb.can_execute() is False
    
    def test_half_open_circuit(self):
        """Test that the circuit transitions to half-open after the reset timeout."""
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=1)
        
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        
        time.sleep(2)
        
        assert cb.can_execute() is True
        assert cb.state == "half-open"
    
    def test_close_circuit_after_success(self):
        """Test that the circuit closes after a successful execution in half-open state."""
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=1)
        
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        
        time.sleep(2)
        
        assert cb.can_execute() is True
        assert cb.state == "half-open"
        
        cb.record_success()
        assert cb.state == "closed"
        assert cb.failure_count == 0
    
    def test_remain_open_after_failure_in_half_open(self):
        """Test that the circuit remains open after a failure in half-open state."""
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=1)
        
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        
        time.sleep(2)
        
        assert cb.can_execute() is True
        assert cb.state == "half-open"
        
        cb.record_failure()
        assert cb.state == "open"
        assert cb.failure_count == 4


class TestCircuitBreakerDecorator:
    """Test cases for the circuit_breaker_decorator."""
    
    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """Test that the decorator allows successful execution."""
        mock_cb = MagicMock()
        mock_cb.can_execute.return_value = True
        
        with patch("newsletter_generator.whatsapp.webhook_receiver.ingestion_circuit_breaker", mock_cb):
            @circuit_breaker_decorator
            async def test_func():
                return "success"
            
            result = await test_func()
            
            assert result == "success"
            mock_cb.can_execute.assert_called_once()
            mock_cb.record_success.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_circuit_open(self):
        """Test that the decorator raises CircuitBreakerError when the circuit is open."""
        mock_cb = MagicMock()
        mock_cb.can_execute.return_value = False
        
        with patch("newsletter_generator.whatsapp.webhook_receiver.ingestion_circuit_breaker", mock_cb):
            @circuit_breaker_decorator
            async def test_func():
                return "success"
            
            with pytest.raises(CircuitBreakerError, match="Circuit breaker is open"):
                await test_func()
            
            mock_cb.can_execute.assert_called_once()
            mock_cb.record_success.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_transient_error(self):
        """Test that the decorator records a failure when a TransientError is raised."""
        mock_cb = MagicMock()
        mock_cb.can_execute.return_value = True
        
        with patch("newsletter_generator.whatsapp.webhook_receiver.ingestion_circuit_breaker", mock_cb):
            @circuit_breaker_decorator
            async def test_func():
                raise TransientError("Temporary error")
            
            with pytest.raises(TransientError, match="Temporary error"):
                await test_func()
            
            mock_cb.can_execute.assert_called_once()
            mock_cb.record_failure.assert_called_once()
            mock_cb.record_success.assert_not_called()
