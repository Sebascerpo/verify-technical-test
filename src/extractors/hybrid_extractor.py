"""
Hybrid Extractor.

Orchestrates extraction using structured data first, OCR text as fallback.
"""

from typing import Dict, Optional, Any
from .base import BaseExtractor
from .ocr_extractor import OCRExtractor
from .structured_extractor import StructuredExtractor
from .line_item_extractor import LineItemExtractor
from ..core.logging_config import get_logger
from ..config.settings import get_settings
from .improved_line_item_extractor import ImprovedLineItemExtractor


logger = get_logger(__name__)
settings = get_settings()


class HybridExtractor(BaseExtractor):
    """
    Hybrid extractor that combines structured and OCR extraction.
    
    Uses structured data as primary source, OCR text as fallback.
    """
    
    def __init__(self):
        """Initialize hybrid extractor with sub-extractors."""
        super().__init__()
        self.ocr_extractor = OCRExtractor()
        self.structured_extractor = StructuredExtractor()
        self.line_item_extractor = LineItemExtractor()
        self.improved_extractor = ImprovedLineItemExtractor()  # NEW
    
    def extract_all_fields(
        self,
        ocr_text: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract all required fields using hybrid strategy.
        
        1. First try structured data from Veryfi API
        2. Fall back to OCR text parsing for missing fields
        
        Args:
            ocr_text: Optional OCR text for fallback
            response: Optional full Veryfi API response dictionary
            
        Returns:
            Dictionary containing all extracted invoice data
        """
        # Get OCR text if not provided
        if ocr_text is None and response:
            ocr_text = response.get('ocr_text', '')
        
        # Extract from structured data first (if enabled)
        structured_data = {}
        if response and settings.use_structured_data:
            structured_data = self.structured_extractor.extract_all_fields(response=response)
            # Extract line items from structured data
            structured_data['line_items'] = self.line_item_extractor.extract_from_structured(response)
        
        # If we have OCR text, use it as fallback for missing fields
        ocr_data = {}
        if ocr_text:
            ocr_data = self.ocr_extractor.extract_all_fields(ocr_text=ocr_text)
            # If no structured line items, use OCR line items
            if not structured_data.get('line_items'):
                ocr_data['line_items'] = self.line_item_extractor.extract_from_ocr(ocr_text)
        
        
        if response and settings.use_structured_data:
            line_items = self.line_item_extractor.extract_from_structured(response)
        elif ocr_text:
            line_items = self.line_item_extractor.extract_from_ocr(ocr_text)
        else:
            line_items = []
        
        # IMPROVE line items with better SKU and tax rate (NEW)
        if line_items:
            line_items = self.improved_extractor.extract_and_improve_line_items(
                line_items=line_items,
                response=response,
                ocr_text=ocr_text
            )
        
        
        # Combine: structured data takes priority, OCR as fallback
        result = {
            'vendor_name': structured_data.get('vendor_name') or ocr_data.get('vendor_name') or None,
            'vendor_address': structured_data.get('vendor_address') or ocr_data.get('vendor_address') or None,
            'bill_to_name': structured_data.get('bill_to_name') or ocr_data.get('bill_to_name') or None,
            'invoice_number': structured_data.get('invoice_number') or ocr_data.get('invoice_number') or None,
            'date': structured_data.get('date') or ocr_data.get('date') or None,
            'line_items': line_items  # Now improved!
        }
        
        # Log which source was used
        if structured_data.get('vendor_name'):
            logger.debug("Used structured data for vendor_name")
        elif ocr_data.get('vendor_name'):
            logger.debug("Used OCR text fallback for vendor_name")
        
        return result

