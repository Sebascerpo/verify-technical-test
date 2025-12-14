"""
Format Validator.

Validates that documents match the expected invoice format.
"""

import re
from typing import Optional
from ..config.settings import get_settings
from ..config.patterns import get_patterns
from ..core.logging_config import get_logger
from ..core.interfaces import IValidator

logger = get_logger(__name__)


class FormatValidator(IValidator):
    """
    Validates invoice document format.
    
    Used to exclude documents that don't match expected invoice format.
    """
    
    def __init__(self):
        """Initialize format validator with settings and patterns."""
        self.settings = get_settings()
        self.patterns = get_patterns()
    
    def validate(self, data: any) -> bool:
        """
        Validate invoice format.
        
        Args:
            data: OCR text string to validate
            
        Returns:
            True if format is valid, False otherwise
        """
        if not isinstance(data, str):
            return False
        
        return self.is_valid_invoice_format(data)
    
    def is_valid_invoice_format(self, ocr_text: str) -> bool:
        """
        Determine if the OCR text matches the expected invoice format.
        
        Args:
            ocr_text: Raw OCR text from the document
            
        Returns:
            True if the document matches expected invoice format, False otherwise
        """
        # Check for key invoice indicators
        required_keywords = ['invoice', 'total', 'date']
        found_keywords = sum(
            1 for keyword in required_keywords 
            if keyword.lower() in ocr_text.lower()
        )
        
        # Should have at least required number of keywords
        required_count = self.settings.required_keywords_count
        if found_keywords < required_count:
            logger.debug(f"Found only {found_keywords} required keywords (need {required_count})")
            return False
        
        # Check for price patterns (invoices should have prices)
        price_matches = self.patterns.get_price_pattern().findall(ocr_text)
        min_price_patterns = self.settings.min_price_patterns
        if len(price_matches) < min_price_patterns:
            logger.debug(f"Found only {len(price_matches)} price patterns (need {min_price_patterns})")
            return False
        
        # Check for reasonable length
        min_length = self.settings.min_ocr_length
        if len(ocr_text) < min_length:
            logger.debug(f"OCR text too short: {len(ocr_text)} < {min_length}")
            return False
        
        return True

