"""
Factory pattern for component creation.

Provides centralized component instantiation with dependency injection.
"""

from typing import Dict, Type, Any, Optional, Callable
from .interfaces import IExtractor, IValidator, IClient, IProcessor, IRepository, IConfig


class ComponentFactory:
    """
    Factory for creating application components.
    
    Supports dependency injection and configuration.
    """
    
    def __init__(self, config: Optional[IConfig] = None):
        """
        Initialize factory with optional configuration.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self._registry: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
    
    def register(self, name: str, factory_func: Callable, singleton: bool = False):
        """
        Register a component factory.
        
        Args:
            name: Component name
            factory_func: Factory function
            singleton: Whether to create singleton instances
        """
        self._registry[name] = (factory_func, singleton)
    
    def create(self, name: str, **kwargs) -> Any:
        """
        Create a component instance.
        
        Args:
            name: Component name
            **kwargs: Additional arguments for factory function
            
        Returns:
            Component instance
        """
        if name not in self._registry:
            raise ValueError(f"Component '{name}' not registered")
        
        factory_func, is_singleton = self._registry[name]
        
        if is_singleton and name in self._singletons:
            return self._singletons[name]
        
        instance = factory_func(self, **kwargs)
        
        if is_singleton:
            self._singletons[name] = instance
        
        return instance
    
    def get_config(self) -> Optional[IConfig]:
        """Get configuration object."""
        return self.config


# Global factory instance (can be replaced for testing)
_default_factory: Optional[ComponentFactory] = None


def get_factory() -> ComponentFactory:
    """Get the default factory instance."""
    global _default_factory
    if _default_factory is None:
        _default_factory = ComponentFactory()
    return _default_factory


def set_factory(factory: ComponentFactory):
    """Set the default factory instance (useful for testing)."""
    global _default_factory
    _default_factory = factory

