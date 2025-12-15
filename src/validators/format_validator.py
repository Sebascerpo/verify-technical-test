"""
Format Validator.

Validates that documents match the expected invoice format.
"""

import re
from typing import Optional, Any
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
    
    def validate(self, data: Any) -> bool:
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
        found_keywords_list = [
            keyword for keyword in required_keywords 
            if keyword.lower() in ocr_text.lower()
        ]
        found_keywords = len(found_keywords_list)
        
        # Should have at least required number of keywords
        required_count = self.settings.required_keywords_count
        if found_keywords < required_count:
            logger.info(
                f"Format validation failed: Found only {found_keywords}/{len(required_keywords)} "
                f"required keywords (need {required_count}). "
                f"Found: {found_keywords_list}, Missing: "
                f"{[k for k in required_keywords if k not in found_keywords_list]}"
            )
            return False
        
        # Check for price patterns (invoices should have prices)
        price_matches = self.patterns.get_price_pattern().findall(ocr_text)
        min_price_patterns = self.settings.min_price_patterns
        if len(price_matches) < min_price_patterns:
            logger.info(
                f"Format validation failed: Found only {len(price_matches)} price patterns "
                f"(need {min_price_patterns})"
            )
            return False
        
        # Check for reasonable length
        min_length = self.settings.min_ocr_length
        if len(ocr_text) < min_length:
            logger.info(
                f"Format validation failed: OCR text too short: {len(ocr_text)} characters "
                f"(minimum required: {min_length})"
            )
            return False
        
        logger.debug(
            f"Format validation passed: {found_keywords} keywords found, "
            f"{len(price_matches)} price patterns, {len(ocr_text)} characters"
        )
        return True

