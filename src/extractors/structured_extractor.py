"""
Structured Data Extractor.

Extracts invoice data from Veryfi API structured response.
"""

import re
from typing import Dict, Optional, Any
from .base import BaseExtractor
from ..clients.veryfi_client import VeryfiClient
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class StructuredExtractor(BaseExtractor):
    """
    Extracts invoice data from Veryfi API structured response.
    
    Uses pre-extracted structured fields for high accuracy.
    """
    
    def extract_all_fields(
        self,
        ocr_text: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract all required fields from structured API response.
        
        Args:
            ocr_text: Not used in structured extractor (for interface compatibility)
            response: Full Veryfi API response dictionary
            
        Returns:
            Dictionary containing all extracted invoice data
        """
        if not response:
            return self._empty_result()
        
        return {
            'vendor_name': self.extract_vendor_name(response),
            'vendor_address': self.extract_vendor_address(response),
            'bill_to_name': self.extract_bill_to_name(response),
            'invoice_number': self.extract_invoice_number(response),
            'date': self.extract_date(response),
            'line_items': []  # Line items handled separately
        }
    
    def extract_vendor_name(self, response: Dict[str, Any]) -> Optional[str]:
        """
        Extract vendor name from Veryfi API structured response.
        
        **Field Assumption**: Vendor name is in response['vendor']['name']['value'] or
        response['vendor']['name'], and includes company suffix (Ltd., Inc., LLC).
        
        **Reasoning**:
        - Veryfi API extracts vendor information at document level
        - Vendor name field contains company name with legal suffix
        - Reference: https://faq.veryfi.com/en/articles/5571268-document-data-extraction-fields-explained
        - Veryfi documentation: vendor.name field contains vendor information
        
        **Cleaning**: Applied via `_clean_vendor_name()` to normalize and preserve suffixes.
        
        Args:
            response: Veryfi API response dictionary
            
        Returns:
            Extracted and cleaned vendor name, or None if not found
        """
        vendor_name = VeryfiClient.extract_structured_field(
            response,
            ['vendor', 'name', 'value'],
            alternative_paths=[
                ['vendor', 'name'],
                ['vendor', 'raw_name', 'value'],
                ['vendor', 'raw_name']
            ]
        )
        
        if vendor_name:
            vendor_name_str = str(vendor_name).strip()
            # Clean and normalize the vendor name
            cleaned = self._clean_vendor_name(vendor_name_str)
            return cleaned if cleaned else vendor_name_str
        return None
    
    def extract_vendor_address(self, response: Dict[str, Any]) -> Optional[str]:
        """Extract vendor address from structured response."""
        vendor_address = VeryfiClient.extract_structured_field(
            response,
            ['vendor', 'address', 'value'],
            alternative_paths=[
                ['vendor', 'address'],
                ['vendor', 'raw_address', 'value'],
                ['vendor', 'raw_address']
            ]
        )
        
        if vendor_address:
            return str(vendor_address).strip()
        return None
    
    def extract_bill_to_name(self, response: Dict[str, Any]) -> Optional[str]:
        """Extract bill to name from structured response."""
        bill_to_name = VeryfiClient.extract_structured_field(
            response,
            ['bill_to', 'name'],
            alternative_paths=[]
        )
        
        if bill_to_name:
            return str(bill_to_name).strip()
        return None
    
    def extract_invoice_number(self, response: Dict[str, Any]) -> Optional[str]:
        """Extract invoice number from structured response."""
        invoice_number = VeryfiClient.extract_structured_field(
            response,
            ['invoice_number'],
            alternative_paths=[
                ['invoice_number', 'value']
            ]
        )
        
        if invoice_number:
            return str(invoice_number).strip()
        return None
    
    def extract_date(self, response: Dict[str, Any]) -> Optional[str]:
        """
        Extract date from structured response and format to MM/DD/YYYY (USA format).
        
        **Field Assumption**: Date is in MM/DD/YYYY format (USA format) because
        invoices are from USA companies.
        
        **Reasoning**:
        - Veryfi API extracts date as "document issue/transaction date"
        - Invoices are from USA companies, so dates follow USA format
        - Veryfi may return dates in YYYY-MM-DD format, which we convert to MM/DD/YYYY
        - Reference: https://faq.veryfi.com/en/articles/5571268-document-data-extraction-fields-explained
        
        **Format Conversion**:
        - Input: YYYY-MM-DD (from Veryfi) or other formats
        - Output: MM/DD/YYYY (USA format)
        
        Args:
            response: Veryfi API response dictionary
            
        Returns:
            Date string in MM/DD/YYYY format, or None if not found
        """
        date_value = VeryfiClient.extract_structured_field(
            response,
            ['date'],
            alternative_paths=[
                ['date', 'value']
            ]
        )
        
        if not date_value:
            return None
        
        date_str = str(date_value).strip()
        
        # If already in YYYY-MM-DD format, convert to MM/DD/YYYY
        date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', date_str)
        if date_match:
            year, month, day = date_match.groups()
            return f"{month}/{day}/{year}"  # Convert to MM/DD/YYYY
        
        # Try to parse other formats
        parsed_date = self._parse_date(date_str)
        if parsed_date:
            return parsed_date
        
        return None
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure with empty strings for consistency."""
        return {
            'vendor_name': '',
            'vendor_address': '',
            'bill_to_name': '',
            'invoice_number': '',
            'date': '',
            'line_items': []
        }

