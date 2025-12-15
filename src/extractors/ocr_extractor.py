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
        """
        Extract vendor name from OCR text.
        
        **Field Assumption**: Vendor name is found in "Please make payments to:" section
        or at the top of the document, and includes company suffix (Ltd., Inc., LLC).
        
        **Reasoning**:
        - Veryfi API extracts vendor information at document level
        - Payment instructions section ("Please make payments to:") is most reliable source
        - Vendor name typically appears in first 8-15 lines of document
        - Reference: https://faq.veryfi.com/en/articles/5571268-document-data-extraction-fields-explained
        
        **Extraction Strategy** (priority order):
        1. "Please make payments to:" pattern (highest priority, most reliable)
        2. First few lines of document (fallback)
        3. Vendor name patterns (regex fallback)
        
        **Cleaning**: Applied via `_clean_vendor_name()` to normalize and preserve suffixes.
        
        Args:
            ocr_text: Raw OCR text from the invoice document
            
        Returns:
            Extracted and cleaned vendor name, or None if not found
        """
        # Strategy 1: Payment pattern (highest priority)
        vendor_name = self._extract_vendor_from_payment_pattern(ocr_text)
        if vendor_name:
            return vendor_name
        
        # Strategy 2: First few lines
        vendor_name = self._extract_vendor_from_first_lines(ocr_text)
        if vendor_name:
            return vendor_name
        
        # Strategy 3: Vendor patterns (fallback)
        return self._extract_vendor_from_patterns(ocr_text)
    
    def _extract_vendor_from_payment_pattern(self, ocr_text: str) -> Optional[str]:
        """
        Extract vendor name from "Please make payments to:" pattern.
        
        Args:
            ocr_text: OCR text from invoice
            
        Returns:
            Extracted vendor name or None
        """
        payment_patterns = [
            re.compile(r'please\s+make\s+payments\s+to\s*:?\s*(.+?)(?:\n|$)', re.IGNORECASE | re.MULTILINE),
            re.compile(r'make\s+payments\s+to\s*:?\s*(.+?)(?:\n|$)', re.IGNORECASE | re.MULTILINE),
            re.compile(r'payments\s+should\s+be\s+made\s+to\s*:?\s*(.+?)(?:\n|$)', re.IGNORECASE | re.MULTILINE),
        ]
        
        for pattern in payment_patterns:
            match = pattern.search(ocr_text)
            if not match:
                continue
            
            vendor_name = match.group(1).strip()
            # Clean up: remove any trailing punctuation or extra text
            vendor_name = re.sub(r'[.,;]+$', '', vendor_name).strip()
            
            if not vendor_name or len(vendor_name) <= 2:
                continue
            
            cleaned = self._clean_vendor_name(vendor_name)
            if cleaned:
                logger.debug(f"Extracted vendor name from payment pattern: {cleaned}")
                return cleaned
        
        return None
    
    def _extract_vendor_from_first_lines(self, ocr_text: str) -> Optional[str]:
        """
        Extract vendor name from first few lines of document.
        
        Args:
            ocr_text: OCR text from invoice
            
        Returns:
            Extracted vendor name or None
        """
        lines = ocr_text.split('\n')
        false_positives = [
            'page', 'page 1', 'page 2', 'page 1 of', 'page 2 of',
            'invoice', 'date', 'total', 'amount', 'due',
            'bill to', 'ship to', 'sold to', 'please make payments'
        ]
        
        # Vendor name is typically in the first few lines
        for i, line in enumerate(lines[:15]):
            if not self._is_valid_vendor_line(line, false_positives, i):
                continue
            
            cleaned = self._clean_vendor_name(line)
            if cleaned:
                return cleaned
        
        return None
    
    def _is_valid_vendor_line(self, line: str, false_positives: List[str], line_index: int) -> bool:
        """
        Check if a line is a valid vendor name candidate.
        
        Args:
            line: Line to check
            false_positives: List of false positive keywords
            line_index: Index of line in document
            
        Returns:
            True if line is valid vendor candidate
        """
        line = line.strip()
        if not line:
            return False
        
        line_lower = line.lower()
        
        # Skip obvious false positives
        if any(fp in line_lower for fp in false_positives):
            return False
        
        # Skip lines that are clearly not vendor names
        if re.match(r'^page\s+\d+', line_lower):
            return False
        if re.match(r'^\d+[/-]\d+[/-]\d+', line):  # Dates
            return False
        if re.match(r'^#?\s*\d+', line):  # Invoice numbers
            return False
        
        # Look for company-like patterns
        if len(line) <= 3 or len(line) >= 100:
            return False
        
        if re.match(r'^\d+', line) or re.match(r'^\d{1,2}[/-]', line):
            return False
        
        # Only check first 8 lines
        return line_index < 8
    
    def _extract_vendor_from_patterns(self, ocr_text: str) -> Optional[str]:
        """
        Extract vendor name using regex patterns.
        
        Args:
            ocr_text: OCR text from invoice
            
        Returns:
            Extracted vendor name or None
        """
        for pattern in self.patterns.get_vendor_patterns():
            match = pattern.search(ocr_text)
            if not match:
                continue
            
            result = match.group(1).strip()
            if result and len(result) > 3:
                cleaned = self._clean_vendor_name(result)
                if cleaned:
                    return cleaned
        
        return None
    
    def extract_vendor_address(self, ocr_text: str) -> Optional[str]:
        """
        Extract vendor address from OCR text.
        
        **Field Assumption**: Vendor address is a multi-line address following
        the vendor name, containing street number, street name, city, state, and ZIP code.
        
        **Reasoning**:
        - Veryfi API extracts vendor.address as structured data
        - Address typically appears immediately after vendor name in invoices
        - Multi-line format (2-4 lines) is standard for USA addresses
        - Reference: https://faq.veryfi.com/en/articles/5571268-document-data-extraction-fields-explained
        
        **Extraction Strategy**:
        - Looks for address lines following vendor name
        - Detects street numbers, address keywords (Street, Ave, Road, etc.)
        - Stops at invoice metadata sections (invoice, date, bill to, etc.)
        - Collects 2-4 lines for complete address
        
        Args:
            ocr_text: Raw OCR text from the invoice document
            
        Returns:
            Multi-line vendor address string, or None if not found
        """
        lines = ocr_text.split('\n')
        vendor_name = self.extract_vendor_name(ocr_text)
        
        # Find where address starts
        start_index = self._find_address_start_line(lines, vendor_name)
        if start_index is None:
            # Fallback: use address pattern
            match = self.patterns.get_address_pattern().search(ocr_text)
            if match:
                return match.group(0).strip()
            return None
        
        # Collect address lines
        address_lines = self._collect_address_lines(lines, start_index)
        if address_lines:
            return '\n'.join(address_lines)
        
        # Fallback: use address pattern
        match = self.patterns.get_address_pattern().search(ocr_text)
        if match:
            return match.group(0).strip()
        
        return None
    
    def _find_address_start_line(self, lines: List[str], vendor_name: Optional[str]) -> Optional[int]:
        """
        Find the line index where address collection should start.
        
        Args:
            lines: List of OCR text lines
            vendor_name: Extracted vendor name
            
        Returns:
            Line index to start collecting, or None if not found
        """
        if not vendor_name:
            return None
        
        for i, line in enumerate(lines[:20]):
            line = line.strip()
            if vendor_name.lower() in line.lower():
                return i + 1  # Start collecting after vendor name line
        
        return None
    
    def _collect_address_lines(self, lines: List[str], start_index: int) -> List[str]:
        """
        Collect address lines starting from given index.
        
        Args:
            lines: List of OCR text lines
            start_index: Index to start collecting from
            
        Returns:
            List of address lines
        """
        address_lines = []
        stop_keywords = ['invoice', 'date', 'bill to', 'ship to', 'item', 'description']
        address_keywords = ['street', 'st', 'avenue', 'ave', 'road', 'rd', 'blvd', 'drive', 'dr']
        
        for i in range(start_index, min(start_index + 20, len(lines))):
            line = lines[i].strip()
            
            # Stop at invoice metadata sections
            if any(stop in line.lower() for stop in stop_keywords):
                break
            
            # Check if line looks like an address line
            is_address_line = (
                re.search(r'\d+', line) or
                any(word in line.lower() for word in address_keywords)
            )
            
            if is_address_line:
                address_lines.append(line)
            elif line and len(address_lines) > 0:
                # Continue collecting if we already have address lines
                address_lines.append(line)
                if len(address_lines) >= 4:
                    break
        
        return address_lines
    
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
        """Return empty result structure with empty strings for consistency."""
        return {
            'vendor_name': '',
            'vendor_address': '',
            'bill_to_name': '',
            'invoice_number': '',
            'date': '',
            'line_items': []
        }

