"""
Retry logic and circuit breaker pattern.

Provides robust error handling for API calls and external operations.
"""

import time
from typing import Callable, Optional, Type, Tuple, Any
from functools import wraps
from ..config.settings import get_settings
from ..core.exceptions import APIError
from ..core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


def retry(
    max_attempts: Optional[int] = None,
    delay: Optional[float] = None,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Retry decorator for functions that may fail.
    
    Args:
        max_attempts: Maximum number of retry attempts (default from settings)
        delay: Initial delay between retries in seconds (default from settings)
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry
    """
    max_attempts = max_attempts or settings.max_retries
    delay = delay or settings.retry_delay
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts:
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {current_delay}s..."
                        )
                        
                        if on_retry:
                            on_retry(attempt, e)
                        
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {str(e)}"
                        )
            
            # All attempts failed, raise last exception
            raise last_exception
        
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Prevents cascading failures by stopping requests when service is down.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type that triggers circuit breaker
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = 'closed'  # closed, open, half_open
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception from function
        """
        if self.state == 'open':
            if time.time() - (self.last_failure_time or 0) > self.recovery_timeout:
                self.state = 'half_open'
                logger.info("Circuit breaker transitioning to half-open state")
            else:
                raise APIError("Circuit breaker is open - service unavailable")
        
        try:
            result = func(*args, **kwargs)
            
            # Success - reset failure count
            if self.state == 'half_open':
                self.state = 'closed'
                logger.info("Circuit breaker closed - service recovered")
            
            self.failure_count = 0
            return result
            
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = 'open'
                logger.error(
                    f"Circuit breaker opened after {self.failure_count} failures"
                )
            
            raise
    
    def reset(self):
        """Reset circuit breaker to closed state."""
        self.state = 'closed'
        self.failure_count = 0
        self.last_failure_time = None

