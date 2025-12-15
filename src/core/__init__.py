"""
Core module providing foundational components for the application.

Includes interfaces, exceptions, and utility functions.
"""

from .interfaces import IValidator
from .exceptions import APIError
from .results import Result

__all__ = [
    'IValidator',
    'APIError',
    'Result',
]

