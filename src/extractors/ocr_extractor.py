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
            address = '\n'.join(address_lines)
            # Final cleanup: remove any remaining metadata
            address = self._clean_vendor_address(address)
            if address:
                return address
        
        # Fallback: use address pattern
        match = self.patterns.get_address_pattern().search(ocr_text)
        if match:
            return match.group(0).strip()
        
        return None
    
    def _clean_vendor_address(self, address: str) -> str:
        """
        Clean vendor address by removing metadata, account numbers, and formatting issues.
        
        Args:
            address: Raw address string
            
        Returns:
            Cleaned address string
        """
        if not address:
            return ''
        
        lines = address.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove account numbers (patterns like "24\t1556267" at start)
            line = re.sub(r'^\d+\s*\t\s*\d+', '', line).strip()
            
            # Remove lines that are just metadata
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['account no', 'account number', 'p.o.', 'po number', 'services for month']):
                continue
            
            # Remove tabs
            line = line.replace('\t', ' ')
            
            # Normalize whitespace
            line = ' '.join(line.split())
            
            if line:
                cleaned_lines.append(line)
        
        # Validate address has required components (street and ZIP)
        if cleaned_lines:
            # Check if we have a ZIP code (5 digits)
            has_zip = any(re.search(r'\d{5}(?:-\d{4})?', line) for line in cleaned_lines)
            # Check if we have a street (contains number and street keyword)
            has_street = any(
                re.search(r'\d+', line) and 
                any(keyword in line.lower() for keyword in ['street', 'st', 'ave', 'road', 'rd', 'blvd', 'drive', 'dr'])
                for line in cleaned_lines
            )
            
            # If we have reasonable address components, return it
            if has_zip or has_street:
                return '\n'.join(cleaned_lines)
        
        return ''
    
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
        
        Improved to stop at metadata sections and filter out account numbers.
        
        Args:
            lines: List of OCR text lines
            start_index: Index to start collecting from
            
        Returns:
            List of address lines (cleaned)
        """
        address_lines = []
        # Enhanced stop keywords - stop before invoice metadata
        stop_keywords = [
            'invoice', 'date', 'bill to', 'ship to', 'item', 'description',
            'account no', 'account number', 'p.o.', 'p.o. number', 'po number',
            'services for month', 'services for', 'account', 'po-', 'account:'
        ]
        address_keywords = ['street', 'st', 'avenue', 'ave', 'road', 'rd', 'blvd', 'drive', 'dr']
        
        for i in range(start_index, min(start_index + 15, len(lines))):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                # If we already have address lines, an empty line might be a separator
                if len(address_lines) >= 2:
                    break
                continue
            
            line_lower = line.lower()
            
            # Stop at invoice metadata sections (account numbers, PO numbers, etc.)
            if any(stop in line_lower for stop in stop_keywords):
                break
            
            # Skip lines that look like account numbers or metadata
            # Account numbers often have patterns like: "24\t1556267" or "Account No.\t\t\tP.O. Number"
            if re.match(r'^\d+\s*\t', line) or '\t' in line[:20]:  # Tabs often indicate metadata
                # Check if it contains account-related keywords
                if any(keyword in line_lower for keyword in ['account', 'po', 'p.o.', 'number']):
                    break
                # Otherwise, might be part of address, continue
            
            # Check if line looks like an address line
            is_address_line = (
                re.search(r'\d+', line) or
                any(word in line_lower for word in address_keywords) or
                re.search(r'\d{5}(?:-\d{4})?', line)  # ZIP code pattern
            )
            
            # Validate it's not just metadata (like account numbers)
            # Skip lines that are just numbers with tabs/spaces
            if re.match(r'^\d+\s*[\t\s]*$', line):
                continue
            
            if is_address_line:
                address_lines.append(line)
            elif line and len(address_lines) > 0:
                # Continue collecting if we already have address lines (might be city/state line)
                # But stop if it looks like metadata
                if not any(stop in line_lower for stop in ['account', 'po', 'invoice', 'date']):
                    address_lines.append(line)
                if len(address_lines) >= 4:
                    break
        
        # Clean address lines (remove tabs, extra whitespace)
        cleaned_lines = []
        for line in address_lines:
            # Replace tabs with spaces
            cleaned = line.replace('\t', ' ')
            # Normalize whitespace
            cleaned = ' '.join(cleaned.split())
            if cleaned:
                cleaned_lines.append(cleaned)
        
        return cleaned_lines
    
    def extract_bill_to_name(self, ocr_text: str) -> Optional[str]:
        """
        Extract bill to name from OCR text.
        
        Improved extraction with section-based search and better cleaning.
        """
        lines = ocr_text.split('\n')
        
        # Strategy 1: Look for "Bill To:" section and extract company name
        bill_to_section_start = None
        for i, line in enumerate(lines[:50]):  # Check first 50 lines
            line_lower = line.lower().strip()
            if any(label in line_lower for label in ['bill to', 'billto', 'sold to', 'customer:']):
                bill_to_section_start = i
                break
        
        if bill_to_section_start is not None:
            # Extract company name from lines following "Bill To:"
            for i in range(bill_to_section_start + 1, min(bill_to_section_start + 10, len(lines))):
                line = lines[i].strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Skip lines that look like addresses (contain numbers at start, street keywords)
                if re.match(r'^\d+', line) or any(keyword in line.lower() for keyword in ['street', 'st', 'ave', 'road', 'rd', 'blvd', 'drive', 'dr']):
                    continue
                
                # Skip lines that look like metadata (account no, po number, etc.)
                if any(keyword in line.lower() for keyword in ['account', 'po', 'p.o.', 'services for month', 'invoice', 'date']):
                    continue
                
                # If line looks like a company name (starts with capital letter, reasonable length)
                if re.match(r'^[A-Z][A-Za-z0-9\s&,.\-\']+$', line) and 3 <= len(line) <= 100:
                    cleaned_name = self._clean_company_name(line)
                    if cleaned_name:
                        logger.debug(f"Found bill_to_name via section search: {cleaned_name}")
                        return cleaned_name
        
        # Strategy 2: Use pattern matching (fallback)
        for pattern in self.patterns.get_bill_to_patterns():
            match = pattern.search(ocr_text)
            if match:
                name = match.group(1).strip()
                # Clean up: take first line only, remove extra text
                name = name.split('\n')[0].strip()
                name = name.split(',')[0].strip()  # Remove address parts after comma
                
                # Validate it looks like a company name
                if name and 3 <= len(name) <= 100:
                    # Filter out false positives
                    name_lower = name.lower()
                    false_positives = ['date', 'invoice', 'total', 'amount', 'quantity', 'description']
                    if not any(fp in name_lower for fp in false_positives):
                        cleaned_name = self._clean_company_name(name)
                        if cleaned_name:
                            logger.debug(f"Found bill_to_name via pattern: {cleaned_name}")
                            return cleaned_name
        
        return None
    
    def _clean_company_name(self, name: str) -> Optional[str]:
        """
        Clean and validate company name.
        
        Args:
            name: Raw company name string
            
        Returns:
            Cleaned company name or None if invalid
        """
        if not name:
            return None
        
        cleaned = name.strip()
        
        # Remove common prefixes/suffixes that aren't part of company name
        cleaned = re.sub(r'^(bill\s+to|sold\s+to|customer)\s*:?\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip()
        
        # Remove trailing punctuation that's not part of company name
        cleaned = re.sub(r'[,;]+$', '', cleaned).strip()
        
        # Must be reasonable length
        if len(cleaned) < 3 or len(cleaned) > 100:
            return None
        
        # Should start with letter
        if not cleaned[0].isalpha():
            return None
        
        return cleaned
    
    def extract_invoice_number(self, ocr_text: str) -> Optional[str]:
        """
        Extract invoice number from OCR text.
        
        Improved extraction with false positive filtering and validation.
        """
        lines = ocr_text.split('\n')
        exclusions = self.patterns.get_invoice_number_exclusions()
        
        # Strategy 1: Look for labeled invoice number in header area (first 30 lines)
        header_text = '\n'.join(lines[:30])
        for pattern in self.patterns.get_invoice_number_patterns()[:3]:  # Try labeled patterns first
            matches = pattern.finditer(header_text)
            for match in matches:
                invoice_num = match.group(1) if match.groups() else match.group(0)
                invoice_num = invoice_num.strip() if invoice_num else None
                
                if invoice_num and self._is_valid_invoice_number(invoice_num, exclusions):
                    logger.debug(f"Found invoice number via labeled pattern: {invoice_num}")
                    return invoice_num
        
        # Strategy 2: Look for numeric invoice numbers (6-20 digits) in header area
        # These are often standalone numbers
        numeric_pattern = re.compile(r'\b([0-9]{6,20})\b')
        matches = numeric_pattern.finditer(header_text)
        candidates = []
        
        for match in matches:
            candidate = match.group(1)
            # Skip if it looks like a date, quantity, price, or account number
            if self._is_valid_invoice_number(candidate, exclusions, check_context=True):
                # Check context - invoice numbers usually appear near "Invoice" or "No."
                context_start = max(0, match.start() - 50)
                context_end = min(len(header_text), match.end() + 50)
                context = header_text[context_start:context_end].lower()
                
                # If near invoice-related keywords, it's likely an invoice number
                if any(keyword in context for keyword in ['invoice', 'inv', 'no.', 'number']):
                    candidates.append((match.start(), candidate))
        
        # Return the first valid candidate (usually the most likely one)
        if candidates:
            # Sort by position (earlier in header is more likely)
            candidates.sort(key=lambda x: x[0])
            invoice_num = candidates[0][1]
            logger.debug(f"Found invoice number via numeric pattern: {invoice_num}")
            return invoice_num
        
        # Strategy 3: Fallback to all patterns in full text
        for pattern in self.patterns.get_invoice_number_patterns():
            matches = pattern.finditer(ocr_text)
            for match in matches:
                invoice_num = match.group(1) if match.groups() else match.group(0)
                invoice_num = invoice_num.strip() if invoice_num else None
                
                if invoice_num and self._is_valid_invoice_number(invoice_num, exclusions):
                    logger.debug(f"Found invoice number via fallback pattern: {invoice_num}")
                    return invoice_num
        
        return None
    
    def _is_valid_invoice_number(self, invoice_num: str, exclusions: set, check_context: bool = False) -> bool:
        """
        Validate if a candidate is a valid invoice number.
        
        Args:
            invoice_num: Candidate invoice number
            exclusions: Set of false positive words to exclude
            check_context: Whether to perform additional context checks
            
        Returns:
            True if valid invoice number, False otherwise
        """
        if not invoice_num:
            return False
        
        invoice_num_lower = invoice_num.lower().strip()
        
        # Must be 6-20 characters (typical invoice number length)
        if len(invoice_num) < 6 or len(invoice_num) > 20:
            return False
        
        # Exclude common false positives
        if invoice_num_lower in exclusions:
            return False
        
        # Exclude if it's all lowercase letters (likely a word, not invoice number)
        if invoice_num.isalpha() and invoice_num.islower():
            return False
        
        # Exclude if it looks like a date (contains / or - in date-like pattern)
        if re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', invoice_num):
            return False
        
        # Exclude if it's a year (4 digits between 1900-2100)
        if invoice_num.isdigit() and len(invoice_num) == 4:
            try:
                year = int(invoice_num)
                if 1900 <= year <= 2100:
                    return False
            except ValueError:
                pass
        
        # Prefer numeric invoice numbers (most common format)
        if invoice_num.isdigit():
            return True
        
        # Alphanumeric is acceptable (e.g., "INV-12345")
        if re.match(r'^[A-Z0-9\-]+$', invoice_num, re.IGNORECASE):
            return True
        
        return False
    
    def extract_date(self, ocr_text: str) -> Optional[str]:
        """
        Extract invoice date from OCR text.
        
        Improved extraction with better context awareness and validation.
        """
        lines = ocr_text.split('\n')
        
        # Strategy 1: Look for labeled date in header area (first 30 lines)
        header_text = '\n'.join(lines[:30])
        
        # Try date section patterns first (most reliable)
        for pattern in self.patterns.get_date_section_patterns():
            match = pattern.search(header_text)
            if match:
                date_str = match.group(1).strip()
                # Extract just the date part (might have extra text)
                # Look for date pattern in the extracted string
                for date_pattern in self.patterns.get_date_patterns():
                    date_match = date_pattern.search(date_str)
                    if date_match:
                        parsed_date = self._parse_date(date_match.group(0))
                        if parsed_date and self._is_valid_date(parsed_date):
                            logger.debug(f"Found date via labeled pattern: {parsed_date}")
                            return parsed_date
                # Try parsing the whole string
                parsed_date = self._parse_date(date_str)
                if parsed_date and self._is_valid_date(parsed_date):
                    logger.debug(f"Found date via labeled pattern (full string): {parsed_date}")
                    return parsed_date
        
        # Strategy 2: Look for date patterns in header area (near invoice number or date labels)
        # Extract dates and validate them
        date_candidates = []
        for pattern in self.patterns.get_date_patterns():
            matches = pattern.finditer(header_text)
            for match in matches:
                date_str = match.group(0)
                parsed_date = self._parse_date(date_str)
                if parsed_date and self._is_valid_date(parsed_date):
                    # Check context - dates near "Invoice" or "Date" keywords are more likely
                    context_start = max(0, match.start() - 30)
                    context_end = min(len(header_text), match.end() + 30)
                    context = header_text[context_start:context_end].lower()
                    
                    score = 0
                    if any(keyword in context for keyword in ['invoice', 'date', 'bill']):
                        score += 10
                    if 'due' not in context:  # Prefer invoice date over due date
                        score += 5
                    
                    date_candidates.append((score, match.start(), parsed_date))
        
        # Return the date with highest score (most context matches) and earliest position
        if date_candidates:
            date_candidates.sort(key=lambda x: (-x[0], x[1]))  # Sort by score (desc), then position
            best_date = date_candidates[0][2]
            logger.debug(f"Found date via pattern matching: {best_date}")
            return best_date
        
        # Strategy 3: Search entire text for date patterns (fallback)
        for pattern in self.patterns.get_date_patterns():
            matches = pattern.finditer(ocr_text)
            for match in matches:
                date_str = match.group(0)
                parsed_date = self._parse_date(date_str)
                if parsed_date and self._is_valid_date(parsed_date):
                    logger.debug(f"Found date via fallback pattern: {parsed_date}")
                    return parsed_date
        
        return None
    
    def _is_valid_date(self, date_str: str) -> bool:
        """
        Validate if a parsed date string is reasonable for an invoice.
        
        Args:
            date_str: Date string in MM/DD/YYYY format
            
        Returns:
            True if date is reasonable, False otherwise
        """
        try:
            # Parse the date
            from datetime import datetime
            dt = datetime.strptime(date_str, '%m/%d/%Y')
            
            # Check if date is not too far in the future (max 1 year ahead)
            from datetime import datetime as dt_now
            if dt > dt_now() and (dt - dt_now()).days > 365:
                return False
            
            # Check if date is not too old (max 10 years ago, reasonable for invoices)
            if dt < dt_now() and (dt_now() - dt).days > 3650:
                return False
            
            return True
        except (ValueError, TypeError):
            return False
    
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

