"""
Custom exception hierarchy for the application.

Provides specific exception types for better error handling and debugging.
"""

from typing import Optional


class InvoiceProcessingError(Exception):
    """Base exception for all invoice processing errors."""
    pass


class APIError(InvoiceProcessingError):
    """Raised when API calls fail."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

