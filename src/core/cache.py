"""
Caching utilities.

Provides caching for expensive operations like regex compilation and API responses.
"""

from typing import Dict, Any, Optional, Callable
from functools import wraps
import time
from ..config.settings import get_settings

settings = get_settings()


class SimpleCache:
    """
    Simple in-memory cache with TTL support.
    
    Thread-safe for basic use cases.
    """
    
    def __init__(self, ttl: Optional[int] = None):
        """
        Initialize cache.
        
        Args:
            ttl: Time to live in seconds (None for no expiration)
        """
        self._cache: Dict[str, tuple[Any, float]] = {}
        self.ttl = ttl or settings.cache_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            return None
        
        value, timestamp = self._cache[key]
        
        # Check expiration
        if self.ttl and (time.time() - timestamp) > self.ttl:
            del self._cache[key]
            return None
        
        return value
    
    def set(self, key: str, value: Any):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = (value, time.time())
    
    def clear(self):
        """Clear all cached values."""
        self._cache.clear()
    
    def has(self, key: str) -> bool:
        """Check if key exists in cache (and is not expired)."""
        return self.get(key) is not None


# Global cache instance
_cache: Optional[SimpleCache] = None


def get_cache() -> SimpleCache:
    """Get the global cache instance."""
    global _cache
    if _cache is None:
        _cache = SimpleCache()
    return _cache


def clear_cache():
    """Clear the global cache."""
    global _cache
    if _cache:
        _cache.clear()


def cached(key_func: Optional[Callable] = None, ttl: Optional[int] = None):
    """
    Decorator for caching function results.
    
    Args:
        key_func: Function to generate cache key from arguments
        ttl: Time to live in seconds
    """
    def decorator(func: Callable) -> Callable:
        cache = SimpleCache(ttl=ttl)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Check cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            cache.set(cache_key, result)
            
            return result
        
        return wrapper
    return decorator

