"""
Configuration management module.

Centralizes all configuration including patterns, thresholds, and settings.
"""

from .settings import Settings, get_settings
from .patterns import PatternConfig, get_patterns

__all__ = [
    'Settings',
    'get_settings',
    'PatternConfig',
    'get_patterns',
]

