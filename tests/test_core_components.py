"""
Tests for core infrastructure components.

Tests cache, circuit breaker, and retry logic.
"""

import pytest
import time
from unittest.mock import Mock, patch
from src.core.cache import SimpleCache, get_cache, clear_cache
from src.core.retry import retry, CircuitBreaker
from src.core.results import Result
from src.core.exceptions import APIError


class TestSimpleCache:
    """Test SimpleCache functionality."""
    
    def test_cache_set_get(self):
        """Test basic cache set and get."""
        cache = SimpleCache(ttl=None)
        
        cache.set('key1', 'value1')
        assert cache.get('key1') == 'value1'
    
    def test_cache_expiration(self):
        """Test cache expiration with TTL."""
        cache = SimpleCache(ttl=1)  # 1 second TTL
        
        cache.set('key1', 'value1')
        assert cache.get('key1') == 'value1'
        
        time.sleep(1.1)
        assert cache.get('key1') is None
    
    def test_cache_clear(self):
        """Test cache clearing."""
        cache = SimpleCache()
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        
        cache.clear()
        assert cache.get('key1') is None
        assert cache.get('key2') is None
    
    def test_cache_has(self):
        """Test cache has method."""
        cache = SimpleCache()
        cache.set('key1', 'value1')
        
        assert cache.has('key1') is True
        assert cache.has('key2') is False
    
    def test_get_cache_singleton(self):
        """Test get_cache returns singleton."""
        cache1 = get_cache()
        cache2 = get_cache()
        
        assert cache1 is cache2


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""
    
    def test_circuit_breaker_success(self):
        """Test circuit breaker with successful calls."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        def success_func():
            return "success"
        
        result = breaker.call(success_func)
        assert result == "success"
        assert breaker.state == 'closed'
        assert breaker.failure_count == 0
    
    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
        
        def fail_func():
            raise Exception("Test error")
        
        # First failure
        with pytest.raises(Exception):
            breaker.call(fail_func)
        assert breaker.state == 'closed'
        assert breaker.failure_count == 1
        
        # Second failure - should open
        with pytest.raises(Exception):
            breaker.call(fail_func)
        assert breaker.state == 'open'
        assert breaker.failure_count == 2
    
    def test_circuit_breaker_blocks_when_open(self):
        """Test circuit breaker blocks calls when open."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        breaker.state = 'open'
        breaker.last_failure_time = time.time()
        
        def func():
            return "should not execute"
        
        with pytest.raises(APIError) as exc_info:
            breaker.call(func)
        assert "Circuit breaker is open" in str(exc_info.value)
    
    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=1)
        breaker.state = 'open'
        breaker.last_failure_time = time.time() - 2  # 2 seconds ago
        
        def success_func():
            return "success"
        
        # Should transition to half_open and then closed
        result = breaker.call(success_func)
        assert result == "success"
        assert breaker.state == 'closed'
    
    def test_circuit_breaker_reset(self):
        """Test circuit breaker reset."""
        breaker = CircuitBreaker()
        breaker.state = 'open'
        breaker.failure_count = 5
        
        breaker.reset()
        
        assert breaker.state == 'closed'
        assert breaker.failure_count == 0
        assert breaker.last_failure_time is None


class TestRetry:
    """Test retry decorator."""
    
    def test_retry_success_first_attempt(self):
        """Test retry with success on first attempt."""
        @retry(max_attempts=3)
        def success_func():
            return "success"
        
        result = success_func()
        assert result == "success"
    
    def test_retry_success_after_failures(self):
        """Test retry succeeds after initial failures."""
        attempt_count = [0]
        
        @retry(max_attempts=3, delay=0.1)
        def flaky_func():
            attempt_count[0] += 1
            if attempt_count[0] < 2:
                raise Exception("Temporary failure")
            return "success"
        
        result = flaky_func()
        assert result == "success"
        assert attempt_count[0] == 2
    
    def test_retry_exhausts_attempts(self):
        """Test retry exhausts all attempts."""
        @retry(max_attempts=2, delay=0.1)
        def always_fail():
            raise Exception("Always fails")
        
        with pytest.raises(Exception) as exc_info:
            always_fail()
        assert "Always fails" in str(exc_info.value)


class TestResult:
    """Test Result objects."""
    
    def test_result_success(self):
        """Test success result."""
        result = Result.success_result("test_value")
        
        assert result.is_success()
        assert result.get_value() == "test_value"
        assert result.get_error() is None
    
    def test_result_failure(self):
        """Test failure result."""
        result = Result.failure_result("test_error")
        
        assert result.is_failure()
        assert result.get_error() == "test_error"
        
        with pytest.raises(ValueError):
            result.get_value()

