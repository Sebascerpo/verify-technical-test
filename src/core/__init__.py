"""
Core module providing foundational components for the application.

Includes interfaces, exceptions, dependency injection, and utility functions.
"""

from .interfaces import (
    IExtractor,
    IValidator,
    IClient,
    IProcessor,
    IRepository
)
from .exceptions import (
    ExtractionError,
    ValidationError,
    ProcessingError,
    ConfigurationError,
    APIError
)
from .results import Result, Success, Failure

__all__ = [
    'IExtractor',
    'IValidator',
    'IClient',
    'IProcessor',
    'IRepository',
    'ExtractionError',
    'ValidationError',
    'ProcessingError',
    'ConfigurationError',
    'APIError',
    'Result',
    'Success',
    'Failure',
]

