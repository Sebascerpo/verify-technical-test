"""
Invoice Data Extractor Module

DEPRECATED: This module is maintained for backward compatibility.
New code should use src.extractors.HybridExtractor directly.

This is a compatibility wrapper around the new HybridExtractor.
"""

from typing import Dict, Optional, Any
from .extractors.hybrid_extractor import HybridExtractor
from .validators.format_validator import FormatValidator
from .core.logging_config import get_logger

logger = get_logger(__name__)


class InvoiceExtractor:
    """
    DEPRECATED: Compatibility wrapper for InvoiceExtractor.
    
    This class wraps the new HybridExtractor for backward compatibility.
    New code should use HybridExtractor directly.
    
    Extracts structured invoice data from Veryfi API response and OCR text.
    Uses structured data as primary source, OCR text as fallback.
    """
    
    def __init__(self):
        """Initialize the invoice extractor (wraps HybridExtractor)."""
        self._extractor = HybridExtractor()
        self._validator = FormatValidator()
    
    def extract_all_fields(
        self, 
        ocr_text: Optional[str] = None, 
        response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract all required fields using hybrid strategy.
        
        Args:
            ocr_text: Optional raw OCR text from the invoice
            response: Optional full Veryfi API response dictionary
            
        Returns:
            Dictionary containing all extracted invoice data
        """
        return self._extractor.extract_all_fields(ocr_text=ocr_text, response=response)
    
    def is_valid_invoice_format(self, ocr_text: str) -> bool:
        """
        Determine if the OCR text matches the expected invoice format.
        
        Args:
            ocr_text: Raw OCR text from the document
            
        Returns:
            True if the document matches expected invoice format, False otherwise
        """
        return self._validator.is_valid_invoice_format(ocr_text)
    
    # Delegate all other methods for backward compatibility
    def extract_vendor_name(self, ocr_text: str):
        """Extract vendor name from OCR text (backward compatibility)."""
        from .extractors.ocr_extractor import OCRExtractor
        extractor = OCRExtractor()
        return extractor.extract_vendor_name(ocr_text)
    
    def extract_vendor_address(self, ocr_text: str):
        """Extract vendor address from OCR text (backward compatibility)."""
        from .extractors.ocr_extractor import OCRExtractor
        extractor = OCRExtractor()
        return extractor.extract_vendor_address(ocr_text)
    
    def extract_bill_to_name(self, ocr_text: str):
        """Extract bill to name from OCR text (backward compatibility)."""
        from .extractors.ocr_extractor import OCRExtractor
        extractor = OCRExtractor()
        return extractor.extract_bill_to_name(ocr_text)
    
    def extract_invoice_number(self, ocr_text: str):
        """Extract invoice number from OCR text (backward compatibility)."""
        from .extractors.ocr_extractor import OCRExtractor
        extractor = OCRExtractor()
        return extractor.extract_invoice_number(ocr_text)
    
    def extract_date(self, ocr_text: str):
        """Extract date from OCR text (backward compatibility)."""
        from .extractors.ocr_extractor import OCRExtractor
        extractor = OCRExtractor()
        return extractor.extract_date(ocr_text)
    
    def extract_line_items(self, ocr_text: str):
        """Extract line items from OCR text (backward compatibility)."""
        from .extractors.line_item_extractor import LineItemExtractor
        extractor = LineItemExtractor()
        return extractor.extract_from_ocr(ocr_text)
