"""
Invoice Data Extractor Module

Extracts structured data from Veryfi API response and OCR text.
Uses Veryfi's structured data as primary source, with OCR text parsing as fallback.
"""

import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from .veryfi_client import VeryfiClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InvoiceExtractor:
    """
    Extracts structured invoice data from Veryfi API response and OCR text.
    Uses structured data as primary source, OCR text as fallback.
    """
    
    def __init__(self):
        """Initialize the invoice extractor with regex patterns."""
        # Date patterns (various formats)
        self.date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # MM/DD/YYYY, DD/MM/YYYY
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',    # YYYY/MM/DD
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}',  # Month DD, YYYY
        ]
        
        # Invoice number patterns
        self.invoice_number_patterns = [
            r'(?:invoice|inv|#)\s*:?\s*([A-Z0-9\-]+)',
            r'invoice\s+number\s*:?\s*([A-Z0-9\-]+)',
            r'#\s*([A-Z0-9\-]{4,})',
        ]
        
        # Price patterns
        self.price_pattern = r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
        self.tax_rate_pattern = r'(\d+\.?\d*)\s*%'
        
        # SKU patterns
        self.sku_patterns = [
            r'sku\s*:?\s*([A-Z0-9\-]+)',
            r'item\s*#\s*:?\s*([A-Z0-9\-]+)',
            r'product\s*code\s*:?\s*([A-Z0-9\-]+)',
        ]
    
    def extract_vendor_name(self, ocr_text: str) -> Optional[str]:
        """
        Extract vendor name from OCR text.
        
        Looks for company name patterns, typically at the top of the document.
        
        Args:
            ocr_text: Raw OCR text from the invoice
            
        Returns:
            Vendor name string, or None if not found
        """
        lines = ocr_text.split('\n')
        
        # Vendor name is typically in the first few lines, often in uppercase or title case
        # Look for lines that look like company names (not addresses, not dates)
        for i, line in enumerate(lines[:10]):
            line = line.strip()
            if not line:
                continue
            
            # Skip lines that are clearly not vendor names
            if any(skip in line.lower() for skip in ['invoice', 'date', 'bill to', 'ship to', 'total']):
                continue
            
            # Look for company-like patterns (capitalized, reasonable length)
            if len(line) > 3 and len(line) < 100:
                # Check if it looks like a company name (not all caps address, not a date)
                if not re.match(r'^\d+', line) and not re.match(r'^\d{1,2}[/-]', line):
                    # Often vendor name is on first or second non-empty line
                    if i < 5:
                        return line
        
        # Fallback: look for "from:" or "vendor:" patterns
        vendor_patterns = [
            r'(?:from|vendor|supplier)\s*:?\s*(.+?)(?:\n|$)',
            r'^([A-Z][A-Za-z\s&]+(?:Inc|LLC|Corp|Ltd|Company|Co)\.?)',
        ]
        
        for pattern in vendor_patterns:
            match = re.search(pattern, ocr_text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_vendor_address(self, ocr_text: str) -> Optional[str]:
        """
        Extract vendor address from OCR text.
        
        Args:
            ocr_text: Raw OCR text from the invoice
            
        Returns:
            Vendor address string (multi-line), or None if not found
        """
        lines = ocr_text.split('\n')
        address_lines = []
        
        # Address typically follows vendor name
        vendor_name = self.extract_vendor_name(ocr_text)
        start_collecting = False
        
        for i, line in enumerate(lines[:20]):
            line = line.strip()
            
            # Start collecting after vendor name
            if vendor_name and vendor_name.lower() in line.lower():
                start_collecting = True
                continue
            
            if start_collecting:
                # Stop at common invoice sections
                if any(stop in line.lower() for stop in ['invoice', 'date', 'bill to', 'ship to', 'item', 'description']):
                    break
                
                # Address lines often contain numbers (street numbers, zip codes)
                # or common address words
                if (re.search(r'\d+', line) or 
                    any(word in line.lower() for word in ['street', 'st', 'avenue', 'ave', 'road', 'rd', 'blvd', 'drive', 'dr'])):
                    address_lines.append(line)
                elif line and len(address_lines) > 0:  # Continue collecting if we've started
                    address_lines.append(line)
                    if len(address_lines) >= 4:  # Typical address has 2-4 lines
                        break
        
        if address_lines:
            return '\n'.join(address_lines)
        
        # Fallback: look for address patterns
        address_pattern = r'(\d+\s+[A-Za-z0-9\s,]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr)[\s\S]{0,200}?(?:\d{5}(?:-\d{4})?))'
        match = re.search(address_pattern, ocr_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return None
    
    def extract_bill_to_name(self, ocr_text: str) -> Optional[str]:
        """
        Extract bill to name from OCR text.
        
        Args:
            ocr_text: Raw OCR text from the invoice
            
        Returns:
            Bill to name string, or None if not found
        """
        # Look for "bill to" section
        bill_to_patterns = [
            r'bill\s+to\s*:?\s*(.+?)(?:\n|$)',
            r'bill\s+to\s*:?\s*\n\s*([A-Z][A-Za-z\s&]+)',
        ]
        
        for pattern in bill_to_patterns:
            match = re.search(pattern, ocr_text, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1).strip()
                # Clean up - take first line if multi-line
                name = name.split('\n')[0].strip()
                return name
        
        # Look for "sold to" or "customer"
        alt_patterns = [
            r'sold\s+to\s*:?\s*(.+?)(?:\n|$)',
            r'customer\s*:?\s*(.+?)(?:\n|$)',
        ]
        
        for pattern in alt_patterns:
            match = re.search(pattern, ocr_text, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1).strip().split('\n')[0]
                return name
        
        return None
    
    def extract_invoice_number(self, ocr_text: str) -> Optional[str]:
        """
        Extract invoice number from OCR text.
        
        Args:
            ocr_text: Raw OCR text from the invoice
            
        Returns:
            Invoice number string, or None if not found
        """
        for pattern in self.invoice_number_patterns:
            matches = re.finditer(pattern, ocr_text, re.IGNORECASE)
            for match in matches:
                invoice_num = match.group(1) if match.groups() else match.group(0)
                if invoice_num and len(invoice_num) >= 3:
                    return invoice_num.strip()
        
        return None
    
    def extract_date(self, ocr_text: str) -> Optional[str]:
        """
        Extract invoice date from OCR text.
        
        Args:
            ocr_text: Raw OCR text from the invoice
            
        Returns:
            Date string in ISO format (YYYY-MM-DD), or None if not found
        """
        # Look for "date" label followed by date
        date_section_pattern = r'date\s*:?\s*([^\n]+)'
        match = re.search(date_section_pattern, ocr_text, re.IGNORECASE)
        
        if match:
            date_str = match.group(1).strip()
            # Try to parse the date
            parsed_date = self._parse_date(date_str)
            if parsed_date:
                return parsed_date
        
        # Search entire text for date patterns
        for pattern in self.date_patterns:
            matches = re.finditer(pattern, ocr_text)
            for match in matches:
                date_str = match.group(0)
                parsed_date = self._parse_date(date_str)
                if parsed_date:
                    return parsed_date
        
        return None
    
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
        year_match = re.search(r'(\d{4})', date_str)
        month_match = re.search(r'(\d{1,2})', date_str)
        
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
    
    def extract_line_items(self, ocr_text: str) -> List[Dict[str, Any]]:
        """
        Extract line items from OCR text.
        
        Parses table structures to extract SKU, description, quantity, price, tax_rate, and total.
        
        Args:
            ocr_text: Raw OCR text from the invoice
            
        Returns:
            List of dictionaries, each containing line item data
        """
        line_items = []
        lines = ocr_text.split('\n')
        
        # Find the line items section (usually after "item", "description", "qty", etc.)
        item_section_start = -1
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['item', 'description', 'qty', 'quantity', 'price', 'amount']):
                if any(col in line_lower for col in ['sku', 'item', 'description', 'qty', 'quantity', 'price', 'total']):
                    item_section_start = i + 1
                    break
        
        if item_section_start == -1:
            # Try to find numeric patterns that look like line items
            item_section_start = 0
        
        # Parse line items
        current_item = {}
        collecting_description = False
        
        for i in range(item_section_start, len(lines)):
            line = lines[i].strip()
            if not line:
                if current_item and any(current_item.values()):
                    line_items.append(current_item)
                    current_item = {}
                collecting_description = False
                continue
            
            # Stop at totals section
            if any(stop in line.lower() for stop in ['subtotal', 'tax', 'total', 'amount due', 'balance']):
                if current_item and any(current_item.values()):
                    line_items.append(current_item)
                break
            
            # Try to extract SKU
            if not current_item.get('sku'):
                for pattern in self.sku_patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        current_item['sku'] = match.group(1).strip()
                        break
            
            # Try to extract quantity (usually a whole number)
            if not current_item.get('quantity'):
                qty_match = re.search(r'^(\d+)\s+', line)
                if qty_match:
                    try:
                        current_item['quantity'] = float(qty_match.group(1))
                    except ValueError:
                        pass
            
            # Try to extract prices
            prices = re.findall(self.price_pattern, line)
            if prices:
                # Usually: unit price, then total
                price_values = []
                for price_str in prices:
                    try:
                        price_val = float(price_str.replace(',', ''))
                        price_values.append(price_val)
                    except ValueError:
                        continue
                
                if price_values:
                    if not current_item.get('price'):
                        # First price might be unit price
                        current_item['price'] = price_values[0]
                    if len(price_values) > 1 and not current_item.get('total'):
                        current_item['total'] = price_values[-1]
                    elif not current_item.get('total'):
                        current_item['total'] = price_values[0]
            
            # Try to extract tax rate
            if not current_item.get('tax_rate'):
                tax_match = re.search(self.tax_rate_pattern, line)
                if tax_match:
                    try:
                        current_item['tax_rate'] = float(tax_match.group(1))
                    except ValueError:
                        pass
            
            # Description is usually the text that's not a number, SKU, or price
            # Collect description lines
            if not any(char.isdigit() for char in line.replace('.', '').replace(',', '').strip()[:5]):
                # Doesn't start with numbers - likely description
                if current_item.get('description'):
                    current_item['description'] += ' ' + line
                else:
                    current_item['description'] = line
            elif not current_item.get('description') and len(line) > 10:
                # Might be description even if it has some numbers
                current_item['description'] = line
        
        # Add last item if exists
        if current_item and any(current_item.values()):
            line_items.append(current_item)
        
        # Clean up line items - ensure all required fields exist
        cleaned_items = []
        for item in line_items:
            cleaned_item = {
                'sku': item.get('sku') or '',
                'description': item.get('description') or '',
                'quantity': item.get('quantity', 0.0),
                'price': item.get('price', 0.0),
                'tax_rate': item.get('tax_rate', 0.0),
                'total': item.get('total', 0.0)
            }
            # Only add if it has at least description or SKU
            if cleaned_item['description'] or cleaned_item['sku']:
                cleaned_items.append(cleaned_item)
        
        logger.info(f"Extracted {len(cleaned_items)} line items")
        return cleaned_items
    
    def extract_all_fields(self, ocr_text: str = None, response: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Extract all required fields using hybrid strategy.
        If response is provided, uses structured data first, then OCR fallback.
        If only ocr_text is provided, uses OCR parsing only.
        
        Args:
            ocr_text: Optional raw OCR text from the invoice
            response: Optional full Veryfi API response dictionary
            
        Returns:
            Dictionary containing all extracted invoice data
        """
        # If we have structured response, use hybrid strategy
        if response:
            return self.extract_all_fields_hybrid(response, ocr_text)
        
        # Otherwise, use OCR text only (fallback)
        if ocr_text:
            return {
                'vendor_name': self.extract_vendor_name_enhanced(ocr_text) or self.extract_vendor_name(ocr_text),
                'vendor_address': self.extract_vendor_address(ocr_text),
                'bill_to_name': self.extract_bill_to_name(ocr_text),
                'invoice_number': self.extract_invoice_number(ocr_text),
                'date': self.extract_date(ocr_text),
                'line_items': self.extract_line_items(ocr_text)
            }
        
        # Return empty structure if neither provided
        return {
            'vendor_name': None,
            'vendor_address': None,
            'bill_to_name': None,
            'invoice_number': None,
            'date': None,
            'line_items': []
        }
    
    def is_valid_invoice_format(self, ocr_text: str) -> bool:
        """
        Determine if the OCR text matches the expected invoice format.
        
        This is used to exclude documents that don't match the expected format.
        
        Args:
            ocr_text: Raw OCR text from the document
            
        Returns:
            True if the document matches expected invoice format, False otherwise
        """
        # Check for key invoice indicators
        required_keywords = ['invoice', 'total', 'date']
        found_keywords = sum(1 for keyword in required_keywords if keyword.lower() in ocr_text.lower())
        
        # Should have at least 2 out of 3 required keywords
        if found_keywords < 2:
            return False
        
        # Check for price patterns (invoices should have prices)
        price_matches = re.findall(self.price_pattern, ocr_text)
        if len(price_matches) < 1:
            return False
        
        # Check for reasonable length (invoices are typically substantial documents)
        if len(ocr_text) < 100:
            return False
        
        return True
    
    # ==================== Structured Data Extraction Methods ====================
    
    def extract_vendor_name_from_structured(self, response: Dict[str, Any]) -> Optional[str]:
        """
        Extract vendor name from Veryfi API structured response.
        
        Args:
            response: Full Veryfi API response dictionary
            
        Returns:
            Vendor name string, or None if not found
        """
        # Try vendor.name.value first, then vendor.name, then vendor.raw_name.value
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
            return str(vendor_name).strip()
        
        return None
    
    def extract_vendor_address_from_structured(self, response: Dict[str, Any]) -> Optional[str]:
        """
        Extract vendor address from Veryfi API structured response.
        
        Args:
            response: Full Veryfi API response dictionary
            
        Returns:
            Vendor address string, or None if not found
        """
        # Try vendor.address.value first, then vendor.address, then vendor.raw_address.value
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
    
    def extract_bill_to_name_from_structured(self, response: Dict[str, Any]) -> Optional[str]:
        """
        Extract bill to name from Veryfi API structured response.
        
        Args:
            response: Full Veryfi API response dictionary
            
        Returns:
            Bill to name string, or None if not found
        """
        # Try bill_to.name first
        bill_to_name = VeryfiClient.extract_structured_field(
            response,
            ['bill_to', 'name'],
            alternative_paths=[]
        )
        
        if bill_to_name:
            return str(bill_to_name).strip()
        
        return None
    
    def extract_invoice_number_from_structured(self, response: Dict[str, Any]) -> Optional[str]:
        """
        Extract invoice number from Veryfi API structured response.
        
        Args:
            response: Full Veryfi API response dictionary
            
        Returns:
            Invoice number string, or None if not found
        """
        # invoice_number can be direct string or invoice_number.value
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
    
    def extract_date_from_structured(self, response: Dict[str, Any]) -> Optional[str]:
        """
        Extract date from Veryfi API structured response and format to YYYY-MM-DD.
        
        Args:
            response: Full Veryfi API response dictionary
            
        Returns:
            Date string in ISO format (YYYY-MM-DD), or None if not found
        """
        # date can be direct string or date.value
        date_value = VeryfiClient.extract_structured_field(
            response,
            ['date'],
            alternative_paths=[
                ['date', 'value']
            ]
        )
        
        if not date_value:
            return None
        
        # Veryfi returns dates like "2024-09-06 00:00:00" or "2024-09-06"
        date_str = str(date_value).strip()
        
        # Extract just the date part (YYYY-MM-DD)
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_str)
        if date_match:
            return date_match.group(1)
        
        # Try to parse other formats
        parsed_date = self._parse_date(date_str)
        if parsed_date:
            return parsed_date
        
        return None
    
    def extract_line_items_from_structured(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract line items from Veryfi API structured response.
        
        Args:
            response: Full Veryfi API response dictionary
            
        Returns:
            List of dictionaries, each containing line item data
        """
        line_items = []
        
        if not response or 'line_items' not in response:
            return line_items
        
        veryfi_line_items = response.get('line_items', [])
        
        if not isinstance(veryfi_line_items, list):
            return line_items
        
        for item in veryfi_line_items:
            if not isinstance(item, dict):
                continue
            
            # Extract fields from Veryfi's line item structure
            sku = item.get('sku') or item.get('upc') or ''
            description = item.get('description') or item.get('full_description') or ''
            quantity = item.get('quantity', 0.0)
            price = item.get('price', 0.0)
            tax_rate = item.get('tax_rate', 0.0)
            total = item.get('total', 0.0)
            
            # Convert to proper types
            try:
                quantity = float(quantity) if quantity else 0.0
            except (ValueError, TypeError):
                quantity = 0.0
            
            try:
                price = float(price) if price else 0.0
            except (ValueError, TypeError):
                price = 0.0
            
            try:
                tax_rate = float(tax_rate) if tax_rate else 0.0
            except (ValueError, TypeError):
                tax_rate = 0.0
            
            try:
                total = float(total) if total else 0.0
            except (ValueError, TypeError):
                total = 0.0
            
            # Only add if we have at least a description or SKU
            if description or sku:
                line_items.append({
                    'sku': str(sku).strip() if sku else '',
                    'description': str(description).strip() if description else '',
                    'quantity': quantity,
                    'price': price,
                    'tax_rate': tax_rate,
                    'total': total
                })
        
        logger.info(f"Extracted {len(line_items)} line items from structured data")
        return line_items
    
    def extract_all_fields_from_structured(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract all required fields from Veryfi API structured response.
        
        Args:
            response: Full Veryfi API response dictionary
            
        Returns:
            Dictionary containing all extracted invoice data
        """
        return {
            'vendor_name': self.extract_vendor_name_from_structured(response),
            'vendor_address': self.extract_vendor_address_from_structured(response),
            'bill_to_name': self.extract_bill_to_name_from_structured(response),
            'invoice_number': self.extract_invoice_number_from_structured(response),
            'date': self.extract_date_from_structured(response),
            'line_items': self.extract_line_items_from_structured(response)
        }
    
    # ==================== Enhanced OCR Text Parsing (Fallback) ====================
    
    def extract_vendor_name_enhanced(self, ocr_text: str) -> Optional[str]:
        """
        Enhanced vendor name extraction from OCR text with better filtering.
        
        Args:
            ocr_text: Raw OCR text from the invoice
            
        Returns:
            Vendor name string, or None if not found
        """
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
                # Check if it looks like a company name
                if not re.match(r'^\d+', line) and not re.match(r'^\d{1,2}[/-]', line):
                    # Often vendor name is on first or second non-empty line
                    if i < 8:
                        return line
        
        # Fallback: look for "from:" or "vendor:" patterns
        vendor_patterns = [
            r'(?:from|vendor|supplier)\s*:?\s*(.+?)(?:\n|$)',
            r'^([A-Z][A-Za-z\s&]+(?:Inc|LLC|Corp|Ltd|Company|Co)\.?)',
        ]
        
        for pattern in vendor_patterns:
            match = re.search(pattern, ocr_text, re.IGNORECASE | re.MULTILINE)
            if match:
                result = match.group(1).strip()
                if result and len(result) > 3:
                    return result
        
        return None
    
    # ==================== Hybrid Extraction Strategy ====================
    
    def extract_all_fields_hybrid(self, response: Dict[str, Any], ocr_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract all required fields using hybrid strategy:
        1. First try structured data from Veryfi API
        2. Fall back to OCR text parsing for missing fields
        
        Args:
            response: Full Veryfi API response dictionary
            ocr_text: Optional OCR text for fallback (extracted from response if not provided)
            
        Returns:
            Dictionary containing all extracted invoice data
        """
        # Get OCR text if not provided
        if ocr_text is None and response:
            ocr_text = response.get('ocr_text', '')
        
        # Extract from structured data first
        structured_data = self.extract_all_fields_from_structured(response) if response else {}
        
        # If we have OCR text, use it as fallback for missing fields
        ocr_data = {}
        if ocr_text:
            ocr_data = self.extract_all_fields(ocr_text)
        
        # Combine: structured data takes priority, OCR as fallback
        result = {
            'vendor_name': structured_data.get('vendor_name') or ocr_data.get('vendor_name') or None,
            'vendor_address': structured_data.get('vendor_address') or ocr_data.get('vendor_address') or None,
            'bill_to_name': structured_data.get('bill_to_name') or ocr_data.get('bill_to_name') or None,
            'invoice_number': structured_data.get('invoice_number') or ocr_data.get('invoice_number') or None,
            'date': structured_data.get('date') or ocr_data.get('date') or None,
            'line_items': structured_data.get('line_items') or ocr_data.get('line_items') or []
        }
        
        # Log which source was used
        if structured_data.get('vendor_name'):
            logger.info("Used structured data for vendor_name")
        elif ocr_data.get('vendor_name'):
            logger.info("Used OCR text fallback for vendor_name")
        
        return result

