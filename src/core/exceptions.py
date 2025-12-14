"""
Custom exception hierarchy for the application.

Provides specific exception types for better error handling and debugging.
"""

from typing import Optional


class InvoiceProcessingError(Exception):
    """Base exception for all invoice processing errors."""
    pass


class ExtractionError(InvoiceProcessingError):
    """Raised when data extraction fails."""
    pass


class ValidationError(InvoiceProcessingError):
    """Raised when validation fails."""
    pass


class ProcessingError(InvoiceProcessingError):
    """Raised when document processing fails."""
    pass


class ConfigurationError(InvoiceProcessingError):
    """Raised when configuration is invalid or missing."""
    pass


class APIError(InvoiceProcessingError):
    """Raised when API calls fail."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class FileNotFoundError(InvoiceProcessingError):
    """Raised when a required file is not found."""
    pass


class FormatError(ValidationError):
    """Raised when document format is invalid."""
    pass

