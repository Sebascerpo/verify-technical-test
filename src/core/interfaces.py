"""
Interface definitions using Python Protocols.

Defines contracts for components that are actually used.
"""

from typing import Protocol, Any


class IValidator(Protocol):
    """Protocol for validators."""
    
    def validate(self, data: Any) -> bool:
        """
        Validate data.
        
        Args:
            data: Data to validate
            
        Returns:
            True if valid, False otherwise
        """
        ...

