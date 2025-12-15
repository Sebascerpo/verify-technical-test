"""
Interface definitions using Python Protocols.

This module defines contracts/interfaces for components using Python's Protocol
feature (structural subtyping/duck typing). Protocols allow for flexible,
type-safe interfaces without requiring explicit inheritance.

The IValidator Protocol defines a contract that any validator class must implement,
enabling polymorphism and making the codebase more extensible and testable.

Example usage:
    class MyValidator:
        def validate(self, data: Any) -> bool:
            # Implementation
            return True
    
    # MyValidator automatically satisfies IValidator Protocol
    validator: IValidator = MyValidator()
"""

from typing import Protocol, Any, runtime_checkable


@runtime_checkable
class IValidator(Protocol):
    """
    Protocol defining the contract for validator classes.
    
    This Protocol uses Python's structural subtyping (duck typing) to define
    a contract that any validator must satisfy. Classes that implement a
    `validate` method with the correct signature automatically satisfy this
    Protocol, without needing to explicitly inherit from it.
    
    This design pattern provides:
    - Type safety: Type checkers can verify Protocol compliance
    - Flexibility: Any class with the right method signature works
    - Extensibility: Easy to add new validators without changing base classes
    - Testability: Easy to create mock validators for testing
    
    Implementations:
    - FormatValidator: Validates invoice document format
    - DataValidator: Validates extracted invoice data structure
    
    Example:
        class CustomValidator:
            def validate(self, data: Any) -> bool:
                return isinstance(data, dict)
        
        # CustomValidator automatically satisfies IValidator Protocol
        validator: IValidator = CustomValidator()
        result = validator.validate({"key": "value"})
    """
    
    def validate(self, data: Any) -> bool:
        """
        Validate data according to the validator's rules.
        
        This method must be implemented by any class that wants to satisfy
        the IValidator Protocol. The implementation should check if the
        provided data meets the validator's criteria.
        
        Args:
            data: The data to validate. Type can vary depending on validator
                  (e.g., str for FormatValidator, Dict for DataValidator)
            
        Returns:
            True if the data is valid according to the validator's rules,
            False otherwise
            
        Raises:
            No exceptions should be raised. Invalid data should return False.
        """
        ...

