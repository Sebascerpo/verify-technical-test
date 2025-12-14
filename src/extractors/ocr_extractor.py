"""
OCR Text Extractor.

Extracts invoice data from OCR text using regex patterns and NLP techniques.
"""

import re
from typing import Dict, List, Optional, Any
from .base import BaseExtractor
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class OCRExtractor(BaseExtractor):
    """
    Extracts invoice data from OCR text.
    
    Uses regex patterns and text parsing to extract all required fields.
    """
    
    def extract_all_fields(
        self,
        ocr_text: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract all required fields from OCR text.
        
        Args:
            ocr_text: Raw OCR text from the invoice
            response: Not used in OCR extractor (for interface compatibility)
            
        Returns:
            Dictionary containing all extracted invoice data
        """
        if not ocr_text:
            return self._empty_result()
        
        return {
            'vendor_name': self.extract_vendor_name(ocr_text),
            'vendor_address': self.extract_vendor_address(ocr_text),
            'bill_to_name': self.extract_bill_to_name(ocr_text),
            'invoice_number': self.extract_invoice_number(ocr_text),
            'date': self.extract_date(ocr_text),
            'line_items': self.extract_line_items(ocr_text)
        }
    
    def extract_vendor_name(self, ocr_text: str) -> Optional[str]:
        """Extract vendor name from OCR text."""
        lines = ocr_text.split('\n')
        
        # Filter out common false positives
        false_positives = [
            'page', 'page 1', 'page 2', 'page 1 of', 'page 2 of',
            'invoice', 'date', 'total', 'amount', 'due',
            'bill to', 'ship to', 'sold to'
        ]
        
        # Vendor name is typically in the first few lines
        for i, line in enumerate(lines[:15]):
            line = line.strip()
            if not line:
                continue
            
            # Skip obvious false positives
            line_lower = line.lower()
            if any(fp in line_lower for fp in false_positives):
                continue
            
            # Skip lines that are clearly not vendor names
            if re.match(r'^page\s+\d+', line_lower):
                continue
            if re.match(r'^\d+[/-]\d+[/-]\d+', line):  # Dates
                continue
            if re.match(r'^#?\s*\d+', line):  # Invoice numbers
                continue
            
            # Look for company-like patterns
            if len(line) > 3 and len(line) < 100:
                if not re.match(r'^\d+', line) and not re.match(r'^\d{1,2}[/-]', line):
                    if i < 8:
                        return line
        
        # Fallback: use vendor patterns
        for pattern in self.patterns.get_vendor_patterns():
            match = pattern.search(ocr_text)
            if match:
                result = match.group(1).strip()
                if result and len(result) > 3:
                    return result
        
        return None
    
    def extract_vendor_address(self, ocr_text: str) -> Optional[str]:
        """Extract vendor address from OCR text."""
        lines = ocr_text.split('\n')
        address_lines = []
        
        vendor_name = self.extract_vendor_name(ocr_text)
        start_collecting = False
        
        for i, line in enumerate(lines[:20]):
            line = line.strip()
            
            if vendor_name and vendor_name.lower() in line.lower():
                start_collecting = True
                continue
            
            if start_collecting:
                if any(stop in line.lower() for stop in ['invoice', 'date', 'bill to', 'ship to', 'item', 'description']):
                    break
                
                if (re.search(r'\d+', line) or 
                    any(word in line.lower() for word in ['street', 'st', 'avenue', 'ave', 'road', 'rd', 'blvd', 'drive', 'dr'])):
                    address_lines.append(line)
                elif line and len(address_lines) > 0:
                    address_lines.append(line)
                    if len(address_lines) >= 4:
                        break
        
        if address_lines:
            return '\n'.join(address_lines)
        
        # Fallback: use address pattern
        match = self.patterns.get_address_pattern().search(ocr_text)
        if match:
            return match.group(1).strip()
        
        return None
    
    def extract_bill_to_name(self, ocr_text: str) -> Optional[str]:
        """Extract bill to name from OCR text."""
        for pattern in self.patterns.get_bill_to_patterns():
            match = pattern.search(ocr_text)
            if match:
                name = match.group(1).strip()
                name = name.split('\n')[0].strip()
                return name
        
        return None
    
    def extract_invoice_number(self, ocr_text: str) -> Optional[str]:
        """Extract invoice number from OCR text."""
        for pattern in self.patterns.get_invoice_number_patterns():
            matches = pattern.finditer(ocr_text)
            for match in matches:
                invoice_num = match.group(1) if match.groups() else match.group(0)
                if invoice_num and len(invoice_num) >= 3:
                    return invoice_num.strip()
        
        return None
    
    def extract_date(self, ocr_text: str) -> Optional[str]:
        """Extract invoice date from OCR text."""
        # Look for "date" label followed by date
        match = self.patterns.get_date_section_pattern().search(ocr_text)
        
        if match:
            date_str = match.group(1).strip()
            parsed_date = self._parse_date(date_str)
            if parsed_date:
                return parsed_date
        
        # Search entire text for date patterns
        for pattern in self.patterns.get_date_patterns():
            matches = pattern.finditer(ocr_text)
            for match in matches:
                date_str = match.group(0)
                parsed_date = self._parse_date(date_str)
                if parsed_date:
                    return parsed_date
        
        return None
    
    def extract_line_items(self, ocr_text: str) -> List[Dict[str, Any]]:
        """Extract line items from OCR text."""
        from .line_item_extractor import LineItemExtractor
        line_item_extractor = LineItemExtractor()
        return line_item_extractor.extract_from_ocr(ocr_text)
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            'vendor_name': None,
            'vendor_address': None,
            'bill_to_name': None,
            'invoice_number': None,
            'date': None,
            'line_items': []
        }

