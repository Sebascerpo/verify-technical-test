"""
Result objects for functional error handling.

Provides a clean way to handle success/failure without exceptions.
"""

from typing import Optional, Any, Generic, TypeVar
from dataclasses import dataclass

T = TypeVar('T')


@dataclass
class Result(Generic[T]):
    """Base result class for operation outcomes."""
    
    success: bool
    value: Optional[T] = None
    error: Optional[str] = None
    
    @classmethod
    def success_result(cls, value: T) -> 'Result[T]':
        """Create a success result."""
        return cls(success=True, value=value)
    
    @classmethod
    def failure_result(cls, error: str) -> 'Result[T]':
        """Create a failure result."""
        return cls(success=False, error=error)
    
    def is_success(self) -> bool:
        """Check if result is successful."""
        return self.success
    
    def is_failure(self) -> bool:
        """Check if result is a failure."""
        return not self.success
    
    def get_value(self) -> T:
        """Get the value, raising error if failure."""
        if not self.success:
            raise ValueError(f"Result is a failure: {self.error}")
        return self.value
    
    def get_error(self) -> Optional[str]:
        """Get the error message."""
        return self.error

