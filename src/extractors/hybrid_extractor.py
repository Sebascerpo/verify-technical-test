"""
Hybrid Extractor.

Orchestrates extraction using structured data first, OCR text as fallback.
"""

from typing import Dict, Optional, Any, List
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
        
        # Extract from structured and OCR data
        structured_data = self._extract_structured_data(response)
        ocr_data = self._extract_ocr_data(ocr_text, structured_data)
        
        # Extract and improve line items
        line_items = self._extract_and_improve_line_items(response, ocr_text, structured_data)
        
        # Combine fields with vendor name priority logic
        result = self._combine_extracted_fields(structured_data, ocr_data, line_items, ocr_text)
        
        return result
    
    def _extract_structured_data(self, response: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract data from structured API response.
        
        Args:
            response: Veryfi API response dictionary
            
        Returns:
            Dictionary with extracted structured data
        """
        if not response or not settings.use_structured_data:
            return {}
        
        structured_data = self.structured_extractor.extract_all_fields(response=response)
        structured_data['line_items'] = self.line_item_extractor.extract_from_structured(response)
        return structured_data
    
    def _extract_ocr_data(self, ocr_text: Optional[str], structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract data from OCR text.
        
        Args:
            ocr_text: OCR text from invoice
            structured_data: Already extracted structured data
            
        Returns:
            Dictionary with extracted OCR data
        """
        if not ocr_text:
            return {}
        
        ocr_data = self.ocr_extractor.extract_all_fields(ocr_text=ocr_text)
        
        # If no structured line items, use OCR line items
        if not structured_data.get('line_items'):
            ocr_data['line_items'] = self.line_item_extractor.extract_from_ocr(ocr_text)
        
        return ocr_data
    
    def _extract_and_improve_line_items(
        self,
        response: Optional[Dict[str, Any]],
        ocr_text: Optional[str],
        structured_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract and improve line items.
        
        Args:
            response: Veryfi API response
            ocr_text: OCR text
            structured_data: Structured data already extracted
            
        Returns:
            List of improved line items
        """
        # Extract line items
        if response and settings.use_structured_data:
            line_items = self.line_item_extractor.extract_from_structured(response)
        elif ocr_text:
            line_items = self.line_item_extractor.extract_from_ocr(ocr_text)
        else:
            line_items = []
        
        # Improve line items with better SKU and tax rate
        if line_items:
            line_items = self.improved_extractor.extract_and_improve_line_items(
                line_items=line_items,
                response=response,
                ocr_text=ocr_text
            )
        
        return line_items
    
    def _select_vendor_name(
        self,
        structured_data: Dict[str, Any],
        ocr_data: Dict[str, Any],
        ocr_text: Optional[str]
    ) -> Optional[str]:
        """
        Select vendor name with priority: payment pattern > structured > OCR.
        
        Args:
            structured_data: Extracted structured data
            ocr_data: Extracted OCR data
            ocr_text: OCR text for pattern matching
            
        Returns:
            Selected vendor name or None
        """
        # Priority 1: OCR "Please make payments to:" pattern (most reliable)
        if ocr_text:
            payment_vendor = self.ocr_extractor.extract_vendor_name(ocr_text)
            if payment_vendor and self._has_payment_pattern(ocr_text):
                logger.debug("Used vendor name from 'Please make payments to:' pattern in OCR")
                return payment_vendor
        
        # Priority 2: Structured data or regular OCR extraction
        vendor_name = structured_data.get('vendor_name') or ocr_data.get('vendor_name')
        if vendor_name:
            source = "structured data" if structured_data.get('vendor_name') else "OCR text fallback"
            logger.debug(f"Used {source} for vendor_name")
        
        return vendor_name
    
    def _has_payment_pattern(self, ocr_text: str) -> bool:
        """
        Check if OCR text contains payment pattern.
        
        Args:
            ocr_text: OCR text to check
            
        Returns:
            True if payment pattern found
        """
        lower = ocr_text.lower()
        return 'please make payments' in lower or 'make payments to' in lower
    
    def _combine_extracted_fields(
        self,
        structured_data: Dict[str, Any],
        ocr_data: Dict[str, Any],
        line_items: List[Dict[str, Any]],
        ocr_text: Optional[str]
    ) -> Dict[str, Any]:
        """
        Combine extracted fields from all sources.
        
        Args:
            structured_data: Extracted structured data
            ocr_data: Extracted OCR data
            line_items: Improved line items
            ocr_text: OCR text for vendor name selection
            
        Returns:
            Combined result dictionary
        """
        vendor_name = self._select_vendor_name(structured_data, ocr_data, ocr_text)
        
        return {
            'vendor_name': vendor_name,
            'vendor_address': structured_data.get('vendor_address') or ocr_data.get('vendor_address') or None,
            'bill_to_name': structured_data.get('bill_to_name') or ocr_data.get('bill_to_name') or None,
            'invoice_number': structured_data.get('invoice_number') or ocr_data.get('invoice_number') or None,
            'date': structured_data.get('date') or ocr_data.get('date') or None,
            'line_items': line_items
        }

