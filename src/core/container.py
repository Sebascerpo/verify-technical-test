"""
Dependency Injection Container.

Simple DI container for managing component dependencies.
"""

from typing import Dict, Type, Any, Optional, Callable, TypeVar
from .factory import ComponentFactory

T = TypeVar('T')


class DIContainer:
    """
    Dependency Injection Container.
    
    Manages component lifecycle and dependencies.
    """
    
    def __init__(self):
        """Initialize the container."""
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
    
    def register_singleton(self, name: str, instance: Any):
        """
        Register a singleton instance.
        
        Args:
            name: Service name
            instance: Service instance
        """
        self._singletons[name] = instance
        self._services[name] = instance
    
    def register_factory(self, name: str, factory: Callable, singleton: bool = False):
        """
        Register a factory function.
        
        Args:
            name: Service name
            factory: Factory function
            singleton: Whether to create singleton instances
        """
        self._factories[name] = (factory, singleton)
    
    def get(self, name: str, **kwargs) -> Any:
        """
        Get a service instance.
        
        Args:
            name: Service name
            **kwargs: Additional arguments for factory
            
        Returns:
            Service instance
        """
        # Check if already instantiated
        if name in self._services:
            return self._services[name]
        
        # Check if factory exists
        if name in self._factories:
            factory, is_singleton = self._factories[name]
            instance = factory(self, **kwargs)
            
            if is_singleton:
                self._services[name] = instance
            
            return instance
        
        raise ValueError(f"Service '{name}' not registered")
    
    def has(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._services or name in self._factories or name in self._singletons
    
    def clear(self):
        """Clear all registered services (useful for testing)."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()

