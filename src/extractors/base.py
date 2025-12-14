"""
Base extractor classes.

Provides abstract base classes for all extractors.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from ..config.patterns import get_patterns
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class BaseExtractor(ABC):
    """
    Abstract base class for all extractors.
    
    Provides common functionality and defines the interface.
    """
    
    def __init__(self):
        """Initialize base extractor with patterns."""
        self.patterns = get_patterns()
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    def extract_all_fields(
        self,
        ocr_text: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract all required fields.
        
        Args:
            ocr_text: Optional OCR text
            response: Optional API response
            
        Returns:
            Dictionary with extracted data
        """
        pass
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """
        Parse a date string into ISO format.
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            Date string in ISO format (YYYY-MM-DD), or None if parsing fails
        """
        date_str = date_str.strip()
        
        # Try common formats
        formats = [
            '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d',
            '%m-%d-%Y', '%d-%m-%Y', '%Y-%m-%d',
            '%B %d, %Y', '%b %d, %Y',
            '%d %B %Y', '%d %b %Y',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # Try to extract year-month-day from various patterns
        import re
        year_match = re.search(r'(\d{4})', date_str)
        
        if year_match:
            year = year_match.group(1)
            # Try to find month and day
            parts = re.findall(r'\d{1,2}', date_str)
            if len(parts) >= 3:
                try:
                    # Assume MM/DD/YYYY or DD/MM/YYYY
                    if len(parts[0]) == 4:  # YYYY/MM/DD
                        dt = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                    else:  # MM/DD/YYYY or DD/MM/YYYY
                        # Try both interpretations
                        try:
                            dt = datetime(int(parts[2]), int(parts[0]), int(parts[1]))
                        except ValueError:
                            dt = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                    return dt.strftime('%Y-%m-%d')
                except (ValueError, IndexError):
                    pass
        
        return None

